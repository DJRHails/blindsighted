"""ElevenLabs text-to-speech client.

API Documentation: https://elevenlabs.io/docs/api-reference/text-to-speech/convert
"""

import io
import time
from enum import StrEnum
from typing import BinaryIO

import httpx
from loguru import logger

from config import settings


class AudioTag(StrEnum):
    """Audio tags for controlling voice delivery and emotion (Eleven v3).

    Reference: https://elevenlabs.io/docs/prompting-guides/best-practices
    """

    # Emotional directions
    HAPPY = "happy"
    SAD = "sad"
    EXCITED = "excited"
    ANGRY = "angry"
    ANNOYED = "annoyed"
    APPALLED = "appalled"
    THOUGHTFUL = "thoughtful"
    SURPRISED = "surprised"
    CURIOUS = "curious"
    SARCASTIC = "sarcastic"
    MISCHIEVOUS = "mischievously"

    # Delivery style
    WHISPER = "whispers"
    PROFESSIONAL = "professional"
    SYMPATHETIC = "sympathetic"
    QUESTIONING = "questioning"
    REASSURING = "reassuring"
    WARMLY = "warmly"
    NERVOUSLY = "nervously"
    SHEEPISHLY = "sheepishly"
    FRUSTRATED = "frustrated"
    DESPERATELY = "desperately"
    DEADPAN = "deadpan"

    # Laughter
    LAUGHS = "laughs"
    LAUGHS_HARDER = "laughs harder"
    STARTS_LAUGHING = "starts laughing"
    GIGGLING = "giggling"
    CHUCKLES = "chuckles"
    WHEEZING = "wheezing"

    # Breathing & pauses
    SIGHS = "sighs"
    EXHALES = "exhales"
    EXHALES_SHARPLY = "exhales sharply"
    INHALES_DEEPLY = "inhales deeply"
    SHORT_PAUSE = "short pause"
    LONG_PAUSE = "long pause"

    # Throat sounds
    CLEARS_THROAT = "clears throat"
    SWALLOWS = "swallows"
    GULPS = "gulps"
    SNORTS = "snorts"

    # Special effects
    SINGS = "sings"
    SINGING = "singing"
    CRYING = "crying"

    def __str__(self) -> str:
        """Format tag for use in text (wrapped in brackets).

        Returns:
            Tag formatted as [tag] for insertion into text

        Example:
            >>> str(AudioTag.WHISPER)
            '[whispers]'
        """
        return f"[{self.value}]"


class ElevenLabsClient:
    """Client for ElevenLabs text-to-speech API.

    Official API Reference:
        https://elevenlabs.io/docs/api-reference/text-to-speech/convert
    """

    def __init__(self, api_key: str | None = None) -> None:
        """Initialize the ElevenLabs client.

        Args:
            api_key: ElevenLabs API key. If not provided, uses settings.elevenlabs_api_key
        """
        self.api_key = api_key or settings.elevenlabs_api_key
        self.base_url = "https://api.elevenlabs.io/v1"

    async def text_to_speech(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Default voice: Rachel
        model_id: str = "eleven_v3",
        voice_settings: dict[str, float] | None = None,
        output_format: str = "mp3_44100_128",
    ) -> bytes:
        """Convert text to speech using ElevenLabs API.

        API Reference: https://elevenlabs.io/docs/api-reference/text-to-speech/convert

        Args:
            text: The text to convert to speech
            voice_id: The voice ID to use (default: Rachel - 21m00Tcm4TlvDq8ikWAM)
            model_id: Model identifier. Defaults to eleven_v3 (v3 model with audio tag support).
                     Alternatives: eleven_multilingual_v2, eleven_turbo_v2_5, eleven_flash_v2_5
            voice_settings: Optional voice settings with keys:
                          - stability (float): Consistency across pronunciations (0-1)
                          - similarity_boost (float): Voice matching (0-1)
                          - style (float): Expressive variation level (0-1)
                          - use_speaker_boost (bool): Enhanced quality
            output_format: Audio codec as "codec_sample_rate_bitrate"
                         (e.g., "mp3_44100_128", "pcm_16000", "ulaw_8000")

        Returns:
            Audio data as bytes (format specified by output_format)

        Raises:
            ValueError: If text is empty
            httpx.HTTPError: If the API request fails
        """
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")

        url = f"{self.base_url}/text-to-speech/{voice_id}"

        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
        }

        # Default voice settings if not provided
        if voice_settings is None:
            voice_settings = {
                "stability": 0.5,
                "similarity_boost": 0.75,
            }

        payload = {
            "text": text,
            "model_id": model_id,
            "voice_settings": voice_settings,
            "output_format": output_format,
        }

        logger.debug(
            f"Generating TTS for {len(text)} characters with voice {voice_id} "
            f"using model {model_id}"
        )

        start_time = time.time()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()

            audio_data = response.content
            duration = time.time() - start_time
            logger.info(
                f"Generated {len(audio_data)} bytes of {output_format} audio in {duration:.2f}s"
            )
            return audio_data

    async def text_to_speech_stream(
        self,
        text: str,
        voice_id: str = "21m00Tcm4TlvDq8ikWAM",  # Default voice: Rachel
        model_id: str = "eleven_v3",
        voice_settings: dict[str, float] | None = None,
        output_format: str = "mp3_44100_128",
    ) -> BinaryIO:
        """Convert text to speech and return as a file-like object.

        Args:
            text: The text to convert to speech
            voice_id: The voice ID to use (default: Rachel)
            model_id: Model identifier. Defaults to eleven_v3 (v3 model with audio tag support)
            voice_settings: Optional voice settings (stability, similarity_boost)
            output_format: Audio codec format (e.g., "mp3_44100_128")

        Returns:
            Binary file-like object containing audio data

        Raises:
            ValueError: If text is empty
            httpx.HTTPError: If the API request fails
        """
        audio_data = await self.text_to_speech(
            text=text,
            voice_id=voice_id,
            model_id=model_id,
            voice_settings=voice_settings,
            output_format=output_format,
        )
        return io.BytesIO(audio_data)
