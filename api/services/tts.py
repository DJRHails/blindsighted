import pyttsx3
from typing import Optional


class TextToSpeechService:
    """Service for converting text to speech"""

    def __init__(self) -> None:
        self.engine: Optional[pyttsx3.Engine] = None
        self._initialize_engine()

    def _initialize_engine(self) -> None:
        """Initialize the TTS engine"""
        try:
            self.engine = pyttsx3.init()
            if self.engine:
                self.engine.setProperty("rate", 150)  # Speed of speech
                self.engine.setProperty("volume", 0.9)  # Volume (0-1)
        except Exception as e:
            print(f"Warning: Could not initialize TTS engine: {e}")
            self.engine = None

    def speak(self, text: str) -> None:
        """
        Convert text to speech and play it

        Args:
            text: Text to convert to speech
        """
        if not self.engine:
            print(f"TTS not available. Text: {text}")
            return

        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Error during speech: {e}")

    def save_to_file(self, text: str, filename: str) -> None:
        """
        Save speech to an audio file

        Args:
            text: Text to convert
            filename: Output file path
        """
        if not self.engine:
            raise RuntimeError("TTS engine not initialized")

        try:
            self.engine.save_to_file(text, filename)
            self.engine.runAndWait()
        except Exception as e:
            print(f"Error saving audio file: {e}")
            raise


tts_service = TextToSpeechService()
