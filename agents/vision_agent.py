"""LiveKit Agent for vision-based scene description using streaming STT-LLM-TTS pipeline."""

import asyncio
import os
from typing import Optional
from loguru import logger
from dotenv import load_dotenv

from livekit import rtc
from livekit.agents import (
    AgentServer,
    AgentSession,
    Agent,
    JobContext,
    cli,
    llm,
)
from livekit.plugins import openai, elevenlabs, silero

# Load environment variables
load_dotenv()


class VisionAssistant(Agent):
    """Vision-enabled AI assistant that processes video frames with each user turn."""

    def __init__(self) -> None:
        super().__init__(
            instructions="""You are a helpful AI assistant for visually impaired users.
            You have access to their camera feed and describe what you see in the environment.
            Your responses are conversational, concise, and focused on what's most relevant or interesting.
            When describing scenes, prioritize: people, objects, text, spatial layout, and potential hazards.
            Be natural and friendly, avoiding robotic or overly technical language.
            If the user asks about something specific, focus on that in your description."""
        )
        self._latest_frame: Optional[rtc.VideoFrame] = None
        self._video_stream: Optional[rtc.VideoStream] = None
        self._tasks: list[asyncio.Task] = []
        logger.info("VisionAssistant initialized")

    async def on_enter(self) -> None:
        """Called when the agent enters a room. Sets up video stream monitoring."""
        room = self.ctx.room
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
                logger.info(f"Subscribed to existing video track from {remote_participant.identity}")

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
            new_message.content.append(
                llm.ChatImage(image=self._latest_frame)
            )
            # Don't clear the frame - keep it for next turn if user speaks again quickly
        else:
            logger.debug("No video frame available for this turn")

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
            frame_count = 0
            async for event in self._video_stream:
                # Store the latest frame for use in next user turn
                self._latest_frame = event.frame
                frame_count += 1
                if frame_count % 30 == 0:  # Log every 30 frames (~1 sec at 30fps)
                    logger.debug(f"Buffered video frame #{frame_count}")

        # Store the async task
        task = asyncio.create_task(read_stream())
        task.add_done_callback(lambda t: self._tasks.remove(t) if t in self._tasks else None)
        self._tasks.append(task)
        logger.info("Started video frame buffering task")


# Create agent server
server = AgentServer()


@server.rtc_session()
async def vision_agent(ctx: JobContext) -> None:
    """Entry point for the vision assistant agent.

    Uses streaming STT-LLM-TTS pipeline with vision capabilities.
    """
    logger.info(f"Starting vision agent for room: {ctx.room.name}")

    # Configure the agent session with STT-LLM-TTS pipeline
    session = AgentSession(
        # Speech-to-Text: Use Deepgram for fast, accurate transcription
        stt="deepgram/nova-2",

        # LLM: Use Gemini 2.0 Flash via OpenRouter for vision support
        llm=openai.LLM(
            model="google/gemini-2.0-flash-exp:free",
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY"),
        ),

        # Text-to-Speech: Use ElevenLabs for natural voice
        tts=elevenlabs.TTS(
            voice_id=os.getenv("ELEVENLABS_VOICE_ID", "21m00Tcm4TlvDq8ikWAM"),  # Rachel voice
            model_id="eleven_turbo_v2_5",
        ),

        # Voice Activity Detection
        vad=silero.VAD.load(),

        # Turn detection for natural conversation flow
        turn_detection=openai.TurnDetector(),
    )

    # Start the agent session
    await session.start(
        room=ctx.room,
        agent=VisionAssistant(),
    )

    # Generate initial greeting
    await session.generate_reply(
        instructions="Greet the user warmly and let them know you can see their camera feed and are ready to help describe their surroundings."
    )

    logger.info("Vision agent session started successfully")


if __name__ == "__main__":
    # Run the agent worker
    cli.run_app(server)
