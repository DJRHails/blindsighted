"""LiveKit Agent for vision-based scene description using streaming STT-LLM-TTS pipeline."""

import asyncio
import logging
from collections.abc import AsyncGenerator, AsyncIterable

from livekit import rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    FlushSentinel,
    JobContext,
    JobRequest,
    ModelSettings,
    WorkerOptions,
    cli,
    get_job_context,
    llm,
    tokenize,
    tts,
)
from livekit.agents.metrics.base import LLMMetrics, TTSMetrics
from livekit.agents.types import TimedString
from livekit.agents.utils import aio
from livekit.agents.voice.events import ConversationItemAddedEvent, SpeechCreatedEvent
from livekit.plugins import deepgram, elevenlabs, openai, silero
from loguru import logger
from typing_extensions import override

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

    @override
    async def transcription_node(
        self,
        text: AsyncIterable[str | TimedString],
        model_settings: ModelSettings,
    ) -> AsyncGenerator[str | TimedString, None]:
        """Transcription node for the vision assistant."""
        async for chunk in text:
            logger.debug(f"Transcription node received text: {chunk}")
            yield chunk

    @override
    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[llm.FunctionTool],
        model_settings: ModelSettings,
    ) -> AsyncGenerator[llm.ChatChunk | str | FlushSentinel, None]:
        # Insert custom preprocessing here
        async for chunk in Agent.default.llm_node(self, chat_ctx, tools, model_settings):
            # Insert custom postprocessing here
            logger.debug(f"LLM node received chunk: {chunk}")
            yield chunk

    @override
    async def tts_node(
        self,
        text: AsyncIterable[str],
        model_settings: ModelSettings,
    ) -> AsyncGenerator[rtc.AudioFrame, None]:
        """TTS node for the vision assistant."""
        activity = self._get_activity_or_raise()
        assert activity.tts is not None, "tts_node called but no TTS node is available"

        wrapped_tts = activity.tts

        if not activity.tts.capabilities.streaming:
            wrapped_tts = tts.StreamAdapter(
                tts=wrapped_tts,
                sentence_tokenizer=tokenize.blingfire.SentenceTokenizer(retain_format=True),
            )

        conn_options = activity.session.conn_options.tts_conn_options
        async with wrapped_tts.stream(conn_options=conn_options) as stream:

            async def _forward_input() -> None:
                async for chunk in text:
                    logger.info(f"TTS node pushing text: '{chunk}'")
                    stream.push_text(chunk)

                stream.end_input()

            forward_task = asyncio.create_task(_forward_input())
            try:
                async for ev in stream:
                    logger.debug(f"TTS node sending '{ev}'")
                    yield ev.frame
            finally:
                await aio.cancel_and_wait(forward_task)

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

    # Create Deepgram TTS instance
    tts_instance = deepgram.TTS(
        api_key=settings.deepgram_api_key,
        model="aura-asteria-en",
        encoding="linear16",
        sample_rate=24000,
    )

    tts_instance = elevenlabs.TTS(
        api_key=settings.elevenlabs_api_key,
        voice_id=settings.elevenlabs_voice_id,
        model="eleven_turbo_v2_5",
    )

    def _on_tts_text_transform(text: str) -> str:
        logger.info(f"TTS text transform: {text}")
        return text

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

    @session.on("agent_state_changed")
    def _on_agent_state_changed(state) -> None:
        logger.info(f"Agent state changed: {state} - {type(state)}")

    @session.on("metrics_collected")
    def _on_metrics_collected(metrics: LLMMetrics | TTSMetrics) -> None:
        """Log metrics from LLM and TTS components."""
        if isinstance(metrics, LLMMetrics):
            logger.info(
                f"LLM metrics: tokens={metrics.total_tokens} "
                f"(prompt={metrics.prompt_tokens}, completion={metrics.completion_tokens}, "
                f"cached={metrics.prompt_cached_tokens}), "
                f"duration={metrics.duration:.2f}s, ttft={metrics.ttft:.2f}s, "
                f"tokens/sec={metrics.tokens_per_second:.1f}"
            )
        elif isinstance(metrics, TTSMetrics):
            logger.info(
                f"TTS metrics: duration={metrics.duration:.2f}s, "
                f"audio_duration={metrics.audio_duration:.2f}s, "
                f"ttfb={metrics.ttfb:.2f}s, characters={metrics.characters_count}"
            )

    @session.on("conversation_item_added")
    def _on_conversation_item(event: ConversationItemAddedEvent) -> None:
        # event.item is a ChatMessage object
        item = event.item
        if not isinstance(item, llm.ChatMessage):
            logger.debug(f"Unknown conversation item added: {item}")
            return
        # Use text_content to get the full text (not just first content item)
        content = item.text_content or ""
        logger.info(
            f"Conversation item added: role={item.role}, content: '{content}', interrupted={item.interrupted}"
        )

    if session.llm and isinstance(session.llm, llm.LLM):

        @session.llm.on("metrics_collected")
        def _on_session_llm_metrics(metrics: LLMMetrics) -> None:
            logger.info(f"Session LLM metrics: {metrics}")

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
    await session.generate_reply(instructions="Say a 4 sentence description of what you can do.")

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
