"""Gemini API client for direct Google AI calls."""

import httpx

from config import settings


class GeminiClient:
    """Client for calling Gemini via Google AI API."""

    def __init__(self) -> None:
        self.api_key = settings.google_api_key
        self.model = "gemini-2.0-flash-exp"
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def analyze_image(self, image_base64: str, prompt: str) -> str:
        """
        Send image to Gemini and return text response.

        Args:
            image_base64: Base64 encoded image string (without data URL prefix)
            prompt: System/user prompt for the analysis

        Returns:
            Text response from Gemini
        """
        if not self.api_key:
            raise ValueError("Google API key not configured (GOOGLE_API_KEY)")

        url = f"{self.base_url}/models/{self.model}:generateContent"

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_base64,
                            }
                        },
                    ]
                }
            ]
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                url,
                params={"key": self.api_key},
                json=payload,
            )
            response.raise_for_status()
            data = response.json()

            # Extract text from response
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    parts = candidate["content"]["parts"]
                    if len(parts) > 0 and "text" in parts[0]:
                        return parts[0]["text"]

            raise ValueError("No valid response from Gemini")
