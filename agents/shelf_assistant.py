"""
Julie Shelf Assistant - Gemini-powered vision assistant for visually impaired supermarket shopping.

Processes photos from JuliePhotos directory and routes them based on filename flags:
- _low: Navigation mode - guide user positioning OR guide user's hand to selected item
- _high: Identification mode - list all items as CSV and upload to API

Flow:
1. LOW photos guide camera positioning until view is good
2. HIGH photo triggers item identification, generates CSV, uploads to API
3. ElevenLabs voice call uses CSV to help user select an item
4. ElevenLabs posts user choice to API
5. New LOW photos guide user's hand to the selected item
"""

import asyncio
import base64
import os
import time
from datetime import datetime
from pathlib import Path

import google.generativeai as genai
import httpx
from dotenv import load_dotenv
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

# Load env - look for .env in current or agents/ directory
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("agents/.env"):
    load_dotenv("agents/.env")
else:
    load_dotenv()

# API base URL
API_BASE_URL = os.getenv("API_BASE_URL", "https://localhost:8000")


class LocalPhotoManager:
    """
    Manages photo files from ~/Documents/JuliePhotos/.
    Mirrors the Swift PhotoFileManager functionality.
    """

    def __init__(self):
        self.directory_path = os.path.expanduser("~/Documents/JuliePhotos")
        print(f"[LocalPhotoManager] Storage Path: {self.directory_path}")

        # Create directory if it doesn't exist
        Path(self.directory_path).mkdir(parents=True, exist_ok=True)

    def list_photos(self, flag: str | None = None) -> list[str]:
        """Returns a list of filenames in the directory."""
        if not os.path.exists(self.directory_path):
            return []

        photos = [
            f
            for f in os.listdir(self.directory_path)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        if flag:
            photos = [p for p in photos if self.get_flag(p) == flag]

        return photos

    def get_flag(self, filename: str) -> str | None:
        """Parse flag from filename (e.g., photo_..._low.jpg -> 'low')."""
        filename_lower = filename.lower()
        if "_low." in filename_lower:
            return "low"
        if "_high." in filename_lower:
            return "high"
        return None

    def load_image_bytes(self, filename: str) -> bytes | None:
        """Loads an image and returns raw bytes."""
        path = os.path.join(self.directory_path, filename)
        if not os.path.exists(path):
            return None

        with open(path, "rb") as f:
            return f.read()

    def get_mime_type(self, filename: str) -> str:
        """Get MIME type for image file."""
        return "image/png" if filename.lower().endswith(".png") else "image/jpeg"


class APIClient:
    """Client for communicating with the FastAPI backend."""

    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url

    async def upload_csv(self, csv_content: str, filename: str | None = None) -> dict:
        """Upload CSV content to the API."""
        if filename is None:
            filename = f"shelf_items_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        async with httpx.AsyncClient() as client:
            files = {"file": (filename, csv_content.encode(), "text/csv")}
            response = await client.post(f"{self.base_url}/csv/upload", files=files)
            response.raise_for_status()
            return response.json()

    async def get_latest_user_choice(self) -> dict | None:
        """Get the latest unprocessed user choice."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/user-choice/latest",
                params={"unprocessed_only": True},
            )
            if response.status_code == 200:
                return response.json()
            return None

    async def mark_choice_processed(self, choice_id: str) -> None:
        """Mark a user choice as processed."""
        async with httpx.AsyncClient() as client:
            response = await client.patch(
                f"{self.base_url}/user-choice/{choice_id}/processed"
            )
            response.raise_for_status()


class GeminiAgent:
    """Gemini agent wrapper for vision tasks using google-generativeai."""

    def __init__(self, role_name: str, system_prompt: str):
        self.role_name = role_name
        self.system_prompt = system_prompt

        # Configure Gemini
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY environment variable required")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            system_instruction=system_prompt,
        )

    def generate(self, user_content: str, image_bytes: bytes | None = None, mime_type: str = "image/jpeg") -> str:
        """Generate a response from the agent (synchronous for simplicity)."""
        print(f"[{self.role_name}] Processing request...")

        try:
            content_parts = [user_content]

            if image_bytes:
                content_parts.append({
                    "mime_type": mime_type,
                    "data": image_bytes,
                })

            response = self.model.generate_content(content_parts)
            return response.text

        except Exception as e:
            return f"Error: {e}"


# Agent system prompts
NAVIGATION_PROMPT = """You are a navigation assistant helping a visually impaired user position their camera to see a store shelf.

Your job is to analyze the current camera view and guide the user to adjust their position so ALL products on the shelf are visible in the frame.

Instructions:
- Describe what's currently visible in the frame
- Identify if any products appear cut off at the edges (left, right, top, bottom)
- Give clear, concise directions to adjust camera position:
  - "Move left/right" for horizontal adjustments
  - "Move up/down" or "tilt up/down" for vertical adjustments
  - "Step back" if too close, "step forward" if too far
- Use clock positions (12 o'clock = up, 3 o'clock = right, etc.) when helpful
- Keep responses SHORT and actionable - the user needs quick guidance
- If the view looks good and shows the full shelf, say "View looks good - ready for capture"

Example response: "I can see canned goods on the left, but products are cut off on the right. Move your camera slightly to the right to include more of the shelf."
"""

IDENTIFICATION_PROMPT = """You are an item identification assistant for visually impaired users.

You are looking at a store shelf. Your job is to identify ALL products visible and output them as CSV data.

OUTPUT FORMAT - You MUST output ONLY a valid CSV with these exact columns:
item_number,product_name,brand,location,price

Rules:
- First line must be the header: item_number,product_name,brand,location,price
- List EVERY distinct product you can see
- item_number: sequential number starting from 1
- product_name: the product type/name (e.g., "Cola 330ml", "Sparkling Water 500ml")
- brand: the brand name if visible, otherwise "Unknown"
- location: describe using "top/middle/bottom shelf" and "left/center/right" (e.g., "top shelf, left")
- price: the price if visible, otherwise "N/A"
- Do NOT include any text before or after the CSV
- Do NOT use markdown code blocks

Example output:
item_number,product_name,brand,location,price
1,Cola 330ml,Coca-Cola,top shelf left,$1.99
2,Sparkling Water 500ml,Perrier,top shelf center,$2.49
3,Orange Juice 1L,Tropicana,middle shelf left,$3.99
"""

GUIDANCE_PROMPT = """You are a hand-guidance assistant helping a visually impaired user reach for a specific item on a shelf.

The user has selected an item they want. You can see their current camera view (likely showing their hand near the shelf).

Your job is to guide their hand to the exact location of the item.

Instructions:
- The user wants to find: {item_name}
- Its known location is: {item_location}
- Guide their hand using clock positions (12 o'clock = up, 3 o'clock = right, etc.)
- Give distance estimates in centimeters or inches
- If you can see their hand, guide relative to it
- Keep responses SHORT and actionable
- When they're very close, say "You're almost there" or "Got it!"

Example responses:
- "Move your hand to 2 o'clock, about 20 centimeters"
- "Up and slightly right, about 10 centimeters"
- "You're very close - just a bit more to the left"
- "Your hand is right on it!"
"""


class ShelfAssistant:
    """Main assistant that routes images and manages the shopping flow."""

    def __init__(self):
        self.photo_manager = LocalPhotoManager()
        self.api_client = APIClient()

        # Initialize agents
        self.navigation_agent = GeminiAgent("NAVIGATION", NAVIGATION_PROMPT)
        self.identification_agent = GeminiAgent("IDENTIFICATION", IDENTIFICATION_PROMPT)

        # Track state
        self.processed_files: set[str] = set()
        self.current_user_choice: dict | None = None
        self.guidance_agent: GeminiAgent | None = None

    async def check_for_user_choice(self) -> None:
        """Check if there's a pending user choice for guidance mode."""
        try:
            choice = await self.api_client.get_latest_user_choice()
            if choice and choice != self.current_user_choice:
                self.current_user_choice = choice
                print(f"\n[Assistant] User selected: {choice['item_name']}")
                if choice.get("item_location"):
                    print(f"[Assistant] Location: {choice['item_location']}")

                # Create guidance agent with item-specific prompt
                guidance_prompt = GUIDANCE_PROMPT.format(
                    item_name=choice["item_name"],
                    item_location=choice.get("item_location", "unknown"),
                )
                self.guidance_agent = GeminiAgent("GUIDANCE", guidance_prompt)
        except Exception as e:
            print(f"[Assistant] Error checking user choice: {e}")

    async def process_image(self, filename: str) -> str | None:
        """Process an image based on its flag."""
        if filename in self.processed_files:
            print(f"[Assistant] Skipping already processed: {filename}")
            return None

        flag = self.photo_manager.get_flag(filename)
        if flag is None:
            print(f"[Assistant] No flag in filename: {filename} - skipping")
            return None

        image_bytes = self.photo_manager.load_image_bytes(filename)
        if image_bytes is None:
            print(f"[Assistant] Failed to load: {filename}")
            return None

        mime_type = self.photo_manager.get_mime_type(filename)
        self.processed_files.add(filename)

        print(f"\n{'='*60}")
        print(f"[Assistant] Processing: {filename} (flag: {flag})")
        print(f"{'='*60}")

        if flag == "high":
            return await self._process_high_image(image_bytes, mime_type)
        elif flag == "low":
            return await self._process_low_image(image_bytes, mime_type)

        return None

    async def _process_high_image(self, image_bytes: bytes, mime_type: str) -> str:
        """Process HIGH image: identify items and upload CSV."""
        response = self.identification_agent.generate(
            "Identify all products on this shelf and output as CSV.",
            image_bytes,
            mime_type,
        )

        print(f"\n[IDENTIFICATION RESPONSE]\n{response}\n")

        # Upload CSV to API
        try:
            # Clean up response - ensure it's valid CSV
            csv_content = response.strip()

            # Remove markdown code blocks if present
            if csv_content.startswith("```"):
                lines = csv_content.split("\n")
                csv_content = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

            result = await self.api_client.upload_csv(csv_content)
            print(f"[Assistant] CSV uploaded successfully: {result}")
        except Exception as e:
            print(f"[Assistant] Failed to upload CSV: {e}")

        return response

    async def _process_low_image(self, image_bytes: bytes, mime_type: str) -> str:
        """Process LOW image: navigation or hand guidance."""
        # Check for user choice first
        await self.check_for_user_choice()

        if self.current_user_choice and self.guidance_agent:
            # Guidance mode - help user reach their selected item
            response = self.guidance_agent.generate(
                f"Guide my hand to reach {self.current_user_choice['item_name']}.",
                image_bytes,
                mime_type,
            )
            print(f"\n[GUIDANCE RESPONSE]\n{response}\n")

            # Check if user got the item (simple heuristic)
            if any(phrase in response.lower() for phrase in ["got it", "right on it", "you have it", "perfect"]):
                try:
                    await self.api_client.mark_choice_processed(self.current_user_choice["id"])
                    print("[Assistant] Item found! Choice marked as processed.")
                    self.current_user_choice = None
                    self.guidance_agent = None
                except Exception as e:
                    print(f"[Assistant] Failed to mark choice processed: {e}")
        else:
            # Navigation mode - help position camera
            response = self.navigation_agent.generate(
                "Analyze this camera view and guide me to position it.",
                image_bytes,
                mime_type,
            )
            print(f"\n[NAVIGATION RESPONSE]\n{response}\n")

        return response


class PhotoEventHandler(FileSystemEventHandler):
    """Handles file system events for new photos."""

    def __init__(self, assistant: ShelfAssistant, loop: asyncio.AbstractEventLoop):
        self.assistant = assistant
        self.loop = loop

    def on_created(self, event: FileSystemEvent) -> None:
        """Called when a new file is created."""
        if event.is_directory:
            return

        filepath = event.src_path
        filename = os.path.basename(filepath)

        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            return

        print(f"[Watcher] New photo detected: {filename}")

        # Small delay to ensure file is fully written
        time.sleep(0.5)

        asyncio.run_coroutine_threadsafe(
            self.assistant.process_image(filename), self.loop
        )


async def watch_for_photos(assistant: ShelfAssistant) -> None:
    """Start watching the photos directory for new files."""
    loop = asyncio.get_event_loop()
    event_handler = PhotoEventHandler(assistant, loop)
    observer = Observer()
    observer.schedule(
        event_handler, assistant.photo_manager.directory_path, recursive=False
    )
    observer.start()

    print(f"\n[Watcher] Watching: {assistant.photo_manager.directory_path}")
    print("[Watcher] Press Ctrl+C to stop\n")

    try:
        while True:
            # Periodically check for user choice updates
            await assistant.check_for_user_choice()
            await asyncio.sleep(2)
    except asyncio.CancelledError:
        observer.stop()
    finally:
        observer.stop()
        observer.join()


async def process_existing_photos(assistant: ShelfAssistant) -> None:
    """Process any existing unprocessed photos."""
    print("\n[Startup] Checking for existing photos...")

    for flag in ["low", "high"]:
        photos = assistant.photo_manager.list_photos(flag=flag)
        if photos:
            print(f"[Startup] Found {len(photos)} existing {flag} photos")
            for photo in sorted(photos):
                await assistant.process_image(photo)


async def main() -> None:
    """Main entry point for the shelf assistant."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in environment.")
        print("Please set GOOGLE_API_KEY in your .env file.")
        return

    assistant = ShelfAssistant()

    print("\n" + "=" * 60)
    print("Julie Shelf Assistant")
    print("=" * 60)
    print(f"Photos directory: {assistant.photo_manager.directory_path}")
    print(f"API endpoint: {API_BASE_URL}")
    print("\nModes:")
    print("  - LOW flag: Camera positioning / Hand guidance")
    print("  - HIGH flag: Item identification (CSV output)")
    print("=" * 60)

    # Check for existing user choice
    await assistant.check_for_user_choice()

    # Process any existing photos first
    await process_existing_photos(assistant)

    # Start watching for new photos
    await watch_for_photos(assistant)


if __name__ == "__main__":
    asyncio.run(main())
