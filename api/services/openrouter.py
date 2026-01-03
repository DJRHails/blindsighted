import base64
import httpx
from config import settings


class OpenRouterClient:
    """Client for interacting with OpenRouter API"""

    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.model = settings.gemini_model

    async def describe_image(self, image_base64: str) -> str:
        """
        Generate a description of an image using Gemini via OpenRouter

        Args:
            image_base64: Base64 encoded image string

        Returns:
            Text description of the image
        """
        if not self.api_key:
            raise ValueError("OpenRouter API key not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": """Describe this image for a blind or visually impaired person.
                            Focus on:
                            - What is in the scene
                            - Any text visible
                            - Important objects or people
                            - Colors and spatial relationships
                            - Any potential hazards or important information

                            Be concise but informative. Speak in second person.""",
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                        },
                    ],
                }
            ],
            "max_tokens": 300,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=payload
            )
            response.raise_for_status()
            data = response.json()

            if "choices" in data and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]

            raise ValueError("No response from OpenRouter")


openrouter_client = OpenRouterClient()
