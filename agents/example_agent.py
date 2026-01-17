"""LiveKit Agent for vision-based scene description using streaming STT-LLM-TTS pipeline."""

import asyncio
import logging

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobRequest,
    WorkerOptions,
    cli,
    get_job_context,
    llm,
)
from livekit.agents.metrics.base import TTSMetrics
from livekit.agents.voice.events import ConversationItemAddedEvent, SpeechCreatedEvent
from livekit.plugins import deepgram, elevenlabs, openai, silero
from loguru import logger

from config import settings

# Enable debug logging
logging.basicConfig(level=logging.INFO)


class VisionAssistant(Agent):
    """Vision-enabled AI assistant that processes video frames with each user turn."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful AI assistant for visually impaired users.
            You have access to their camera feed and describe what you see in the environment.
            Your responses are conversational, concise, and focused on what's most relevant or interesting.
            When describing scenes, prioritize: people, objects, text, spatial layout, and potential hazards.
            Be natural and friendly, avoiding robotic or overly technical language.
            If the user asks about something specific, focus on that in your description.
            Do not be afraid to say that you don't know - either because you can't see any images in your context.
            """
        )
        self._latest_frame: rtc.VideoFrame | None = None
        self._video_stream: rtc.VideoStream | None = None
        self._tasks: list[asyncio.Task] = []
        logger.info("VisionAssistant initialized")

    async def on_enter(self) -> None:
        """Called when the agent enters a room. Sets up video stream monitoring."""
        ctx = get_job_context()
        room = ctx.room

        logger.info(f"Agent entered room: {room.name}")

        # Find the first video track from remote participant (if any)
        if room.remote_participants:
            remote_participant = list(room.remote_participants.values())[0]
            video_tracks = [
                publication.track
                for publication in list(remote_participant.track_publications.values())
                if publication.track and publication.track.kind == rtc.TrackKind.KIND_VIDEO
            ]
            if video_tracks:
                self._create_video_stream(video_tracks[0])
                logger.info(
                    f"Subscribed to existing video track from {remote_participant.identity}"
                )

        # Watch for new video tracks not yet published
        @room.on("track_subscribed")
        def on_track_subscribed(
            track: rtc.Track,
            publication: rtc.RemoteTrackPublication,
            participant: rtc.RemoteParticipant,
        ) -> None:
            """Handle new track subscription."""
            if track.kind == rtc.TrackKind.KIND_VIDEO:
                logger.info(f"New video track subscribed from {participant.identity}")
                self._create_video_stream(track)

    async def on_user_turn_completed(
        self, chat_ctx: llm.ChatContext, new_message: llm.ChatMessage
    ) -> None:
        """Add the latest video frame to the user's message for vision context."""
        if self._latest_frame:
            logger.info("Attaching latest video frame to user message")
            new_message.content.append(llm.ImageContent(image=self._latest_frame))
            # Don't clear the frame - keep it for next turn if user speaks again quickly
        else:
            logger.warning("No video frame available - video is not streaming")
            # Add a system note for the LLM to inform the user about missing video
            new_message.content.append(
                "[SYSTEM: No video frame available. The user's camera feed is not currently streaming. Please inform them that you cannot see their camera at the moment.]"
            )

    def _create_video_stream(self, track: rtc.Track) -> None:
        """Create a video stream to buffer the latest frame from user's camera."""
        # Close any existing stream (we only want one at a time)
        if self._video_stream is not None:
            logger.info("Closing existing video stream")
            # Cancel existing stream
            for task in self._tasks:
                if not task.done():
                    task.cancel()
            self._tasks.clear()

        # Create a new stream to receive frames
        self._video_stream = rtc.VideoStream(track)
        logger.info("Created new video stream")

        async def read_stream() -> None:
            """Continuously read and buffer the latest video frame."""
            if not self._video_stream:
                logger.error("No video stream available")
                return
            frame_count = 0
            async for event in self._video_stream:
                # Store the latest frame for use in next user turn
                self._latest_frame = event.frame
                frame_count += 1
                if frame_count % 100 == 0:
                    logger.debug(f"Buffered video frame '{track.name}#{frame_count}'")

        # Store the async task
        task = asyncio.create_task(read_stream())
        task.add_done_callback(lambda t: self._tasks.remove(t) if t in self._tasks else None)
        self._tasks.append(task)
        logger.info("Started video frame buffering task")


# Create agent server
server = AgentServer()


async def should_accept_job(job_request: JobRequest) -> None:
    """Filter function to accept only jobs matching this agent's name.

    The agent name is configured via settings.livekit_agent_name
    and should match the agent_id stored in the room metadata by the API.
    """
    agent_name = settings.livekit_agent_name
    room_metadata = job_request.room.metadata

    # If no agent name is configured in the room metadata, accept all jobs (backward compatibility)
    if not room_metadata:
        logger.warning(
            f"Room {job_request.room.name} has no metadata - accepting job for backward compatibility"
        )
        await job_request.accept()
        return

    # Accept job if room metadata matches our agent name
    should_accept = room_metadata == agent_name
    if should_accept:
        logger.info(f"Accepting job for room {job_request.room.name} (agent: {agent_name})")
        await job_request.accept()
        return

    logger.info(
        f"Skipping job for room {job_request.room.name} (expected: {agent_name}, got: {room_metadata})"
    )
    return


async def entrypoint(ctx: JobContext) -> None:
    """Entry point for the vision assistant agent.

    Uses streaming STT-LLM-TTS pipeline with vision capabilities.
    """
    logger.info(f"Starting vision agent for room: {ctx.room.name}")

    await ctx.connect()

    tts_instance = deepgram.TTS(
        api_key=settings.deepgram_api_key,
        model="aura-asteria-en",
        encoding="linear16",
        sample_rate=24000,
    )

    # tts_instance = elevenlabs.TTS(
    #     api_key=settings.elevenlabs_api_key,
    #     voice_id=settings.elevenlabs_voice_id,
    #     model="eleven_turbo_v2_5",
    # )

    # tts_instance = elevenlabs.TTS(
    #     api_key=settings.elevenlabs_api_key,
    #     voice_id=settings.elevenlabs_voice_id,
    #     model="eleven_turbo_v2_5",
    # )

    # Configure the agent session with STT-LLM-TTS pipeline
    session = AgentSession(
        # Speech-to-Text: Use Deepgram for fast, accurate transcription
        stt=deepgram.STT(
            model="nova-3",
            api_key=settings.deepgram_api_key,
        ),
        llm=openai.LLM(
            model="google/gemini-2.5-flash",
            base_url=settings.openrouter_base_url,
            api_key=settings.openrouter_api_key,
            max_completion_tokens=500,  # Ensure longer responses aren't truncated
        ),
        # Text-to-Speech: Use Deepgram TTS
        tts=tts_instance,
        # Voice Activity Detection
        vad=silero.VAD.load(),
        # Interruption settings - ensure user doesn't accidentally interrupt during pauses
        min_interruption_duration=1.0,  # Require 1 second of speech to interrupt (default 0.5)
        allow_interruptions=True,
        use_tts_aligned_transcript=True,
    )

    # Start the agent session
    agent = VisionAssistant()
    await session.start(
        room=ctx.room,
        agent=agent,
    )

    # Add event listeners for debugging
    @session.on("user_input_transcribed")
    def _on_user_input(text: str) -> None:
        logger.info(f"User said: {text}")

    @session.on("speech_created")
    def _on_speech_created(event: SpeechCreatedEvent) -> None:
        handle = event.speech_handle
        logger.info(f"Speech from {event.source} with handle #{handle.id}")

    @session.on("conversation_item_added")
    def _on_conversation_item(event: ConversationItemAddedEvent) -> None:
        # event.item is a ChatMessage object
        item = event.item
        if not isinstance(item, llm.ChatMessage):
            logger.debug(f"Unknown conversation item added: {item}")
            return
        content = item.content[0] if item.content else ""
        logger.info(
            f"Conversation item added: role={item.role}, content: '{content}', interrupted={item.interrupted}"
        )

    # Add session TTS event listeners
    if session.tts:
        logger.info("Setting up session TTS event listeners")

        @session.tts.on("error")
        def _on_session_tts_error(error: Exception) -> None:
            logger.warning(f"Session TTS error: {error}")

        @session.tts.on("metrics_collected")
        def _on_session_tts_metrics(metrics: TTSMetrics) -> None:
            logger.info(f"Session TTS metrics: {metrics}")

    # Generate initial greeting
    await session.generate_reply(instructions="Say 'blind-sighted connected'.")

    logger.info("Vision agent session started successfully")


if __name__ == "__main__":
    logger.info("Starting vision agent worker")
    # Run the agent worker
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
            request_fnc=should_accept_job,
            ws_url=settings.livekit_url,
            api_key=settings.livekit_api_key,
            api_secret=settings.livekit_api_secret,
        )
    )
