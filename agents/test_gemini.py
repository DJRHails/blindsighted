"""
Gemini Agent for processing photos from BlindsightedPhotos directory.

Routes images to different Gemini instances based on filename flags:
- _low: Navigation mode - guide user positioning to see all shelf products
- _high: Identification mode - list all items visible on the shelf
"""

import asyncio
import base64
import os
import time
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import llm
from livekit.plugins import google
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

# Load env - look for .env in current or agents/ directory
if os.path.exists(".env"):
    load_dotenv(".env")
elif os.path.exists("agents/.env"):
    load_dotenv("agents/.env")
else:
    load_dotenv()


class LocalPhotoManager:
    """
    Manages photo files from ~/Documents/BlindsightedPhotos/.
    Mirrors the Swift PhotoFileManager functionality.
    """

    def __init__(self):
        self.directory_path = os.path.expanduser("~/Documents/BlindsightedPhotos")
        print(f"[LocalPhotoManager] Storage Path: {self.directory_path}")

        # Create directory if it doesn't exist
        Path(self.directory_path).mkdir(parents=True, exist_ok=True)

    def list_photos(self, flag: str | None = None) -> list[str]:
        """
        Returns a list of filenames in the directory.

        Args:
            flag: Optional filter - 'low', 'high', or None for all photos
        """
        if not os.path.exists(self.directory_path):
            return []

        photos = [
            f
            for f in os.listdir(self.directory_path)
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        # Filter by flag if specified
        if flag:
            photos = [p for p in photos if self.get_flag(p) == flag]

        return photos

    def get_flag(self, filename: str) -> str | None:
        """
        Parse flag from filename.

        Examples:
            - "photo_2026-01-17_low.jpg" -> "low"
            - "photo_2026-01-17_high.jpg" -> "high"
            - "photo_2026-01-17.jpg" -> None
        """
        filename_lower = filename.lower()
        if "_low." in filename_lower:
            return "low"
        if "_high." in filename_lower:
            return "high"
        return None

    def load_image(self, filename: str) -> str | None:
        """Loads an image and returns a data URL for Gemini."""
        path = os.path.join(self.directory_path, filename)
        if not os.path.exists(path):
            return None

        with open(path, "rb") as f:
            image_bytes = f.read()
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            mime_type = "image/png" if filename.lower().endswith(".png") else "image/jpeg"
            return f"data:{mime_type};base64,{image_b64}"


class GeminiAgent:
    """Generic Gemini agent wrapper for vision tasks."""

    def __init__(self, role_name: str, system_prompt: str, api_key: str):
        self.role_name = role_name
        self.model = google.LLM(
            model="gemini-2.0-flash-exp",
            api_key=api_key,
        )
        self.system_prompt = system_prompt

    async def generate(self, user_content: str, image_data_url: str | None = None) -> str:
        """Generate a response from the agent."""
        chat_ctx = llm.ChatContext()
        chat_ctx.add_message(role="system", content=self.system_prompt)

        # Build user message content
        msg_content: list = [user_content]
        if image_data_url:
            msg_content.append(llm.ImageContent(image=image_data_url))

        chat_ctx.add_message(role="user", content=msg_content)

        print(f"[{self.role_name}] Processing request...")

        try:
            stream = self.model.chat(chat_ctx=chat_ctx)
            full_response = ""
            async for chunk in stream:
                if chunk.delta and chunk.delta.content:
                    full_response += chunk.delta.content
            return full_response
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

You are looking at a store shelf. Your job is to provide a comprehensive list of ALL products visible.

Instructions:
- List EVERY distinct product you can see
- Use this format for each item:
  1. [Product Name/Brand] - [Location on shelf]
- Be specific about brands and product types when visible
- Describe locations using: "top shelf", "middle shelf", "bottom shelf", "left side", "center", "right side"
- If you can read prices, include them
- Group similar items together
- Be thorough - don't miss any products

Start your response with "I can see the following items:" and then list them.
"""


class ImageRouter:
    """Routes images to the appropriate Gemini agent based on their flag."""

    def __init__(self, api_key: str):
        self.photo_manager = LocalPhotoManager()

        # Initialize the two specialized agents
        self.navigation_agent = GeminiAgent("NAVIGATION", NAVIGATION_PROMPT, api_key)
        self.identification_agent = GeminiAgent("IDENTIFICATION", IDENTIFICATION_PROMPT, api_key)

        # Track processed files to avoid duplicates
        self.processed_files: set[str] = set()

    async def process_image(self, filename: str) -> str | None:
        """
        Process an image by routing it to the correct agent based on its flag.

        Args:
            filename: The filename of the image to process

        Returns:
            The agent's response, or None if the image couldn't be processed
        """
        # Skip if already processed
        if filename in self.processed_files:
            print(f"[Router] Skipping already processed file: {filename}")
            return None

        # Get the flag from filename
        flag = self.photo_manager.get_flag(filename)
        if flag is None:
            print(f"[Router] No flag found in filename: {filename} - skipping")
            return None

        # Load the image
        image_url = self.photo_manager.load_image(filename)
        if image_url is None:
            print(f"[Router] Failed to load image: {filename}")
            return None

        # Mark as processed
        self.processed_files.add(filename)

        # Route to appropriate agent
        print(f"\n{'='*60}")
        print(f"[Router] Processing: {filename} (flag: {flag})")
        print(f"{'='*60}")

        if flag == "low":
            response = await self.navigation_agent.generate(
                "Analyze this camera view and guide me to position it so I can see the entire shelf.",
                image_url,
            )
            print(f"\n[NAVIGATION RESPONSE]\n{response}\n")
        elif flag == "high":
            response = await self.identification_agent.generate(
                "List all the products you can see on this shelf.", image_url
            )
            print(f"\n[IDENTIFICATION RESPONSE]\n{response}\n")
        else:
            return None

        return response


class PhotoEventHandler(FileSystemEventHandler):
    """Handles file system events for new photos."""

    def __init__(self, router: ImageRouter, loop: asyncio.AbstractEventLoop):
        self.router = router
        self.loop = loop

    def on_created(self, event: FileSystemEvent) -> None:
        """Called when a new file is created."""
        if event.is_directory:
            return

        filepath = event.src_path
        filename = os.path.basename(filepath)

        # Only process image files
        if not filename.lower().endswith((".jpg", ".jpeg", ".png")):
            return

        print(f"[Watcher] New photo detected: {filename}")

        # Small delay to ensure file is fully written
        time.sleep(0.5)

        # Schedule the async processing in the event loop
        asyncio.run_coroutine_threadsafe(self.router.process_image(filename), self.loop)


async def watch_for_photos(router: ImageRouter) -> None:
    """Start watching the photos directory for new files."""
    loop = asyncio.get_event_loop()
    event_handler = PhotoEventHandler(router, loop)
    observer = Observer()
    observer.schedule(event_handler, router.photo_manager.directory_path, recursive=False)
    observer.start()

    print(f"\n[Watcher] Watching for new photos in: {router.photo_manager.directory_path}")
    print("[Watcher] Press Ctrl+C to stop\n")

    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        observer.stop()
    finally:
        observer.stop()
        observer.join()


async def process_existing_photos(router: ImageRouter) -> None:
    """Process any existing unprocessed photos in the directory."""
    print("\n[Startup] Checking for existing photos...")

    # Process low flag photos first, then high
    for flag in ["low", "high"]:
        photos = router.photo_manager.list_photos(flag=flag)
        if photos:
            print(f"[Startup] Found {len(photos)} existing {flag} photos")
            for photo in sorted(photos):  # Sort by name (which includes timestamp)
                await router.process_image(photo)


async def main() -> None:
    """Main entry point for the image routing agent."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found in environment.")
        print("Please set GOOGLE_API_KEY in your .env file.")
        return

    # Create the router with both agents
    router = ImageRouter(api_key)

    print("\n" + "=" * 60)
    print("Blindsighted Image Router")
    print("=" * 60)
    print(f"Photos directory: {router.photo_manager.directory_path}")
    print("Agents:")
    print("  - NAVIGATION (low flag): Guides camera positioning")
    print("  - IDENTIFICATION (high flag): Lists shelf items")
    print("=" * 60)

    # Process any existing photos first
    await process_existing_photos(router)

    # Start watching for new photos
    await watch_for_photos(router)


async def test_single_image(image_path: str, flag: str = "high") -> None:
    """
    Test function to process a single image directly.

    Args:
        image_path: Path to the image file
        flag: 'low' for navigation, 'high' for identification
    """
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("Error: GOOGLE_API_KEY not found.")
        return

    if not os.path.exists(image_path):
        print(f"Error: Image not found: {image_path}")
        return

    # Load image
    with open(image_path, "rb") as f:
        image_bytes = f.read()
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")
        mime_type = "image/png" if image_path.endswith(".png") else "image/jpeg"
        image_url = f"data:{mime_type};base64,{image_b64}"

    # Create appropriate agent
    if flag == "low":
        agent = GeminiAgent("NAVIGATION", NAVIGATION_PROMPT, api_key)
        prompt = "Analyze this camera view and guide me to position it so I can see the entire shelf."
    else:
        agent = GeminiAgent("IDENTIFICATION", IDENTIFICATION_PROMPT, api_key)
        prompt = "List all the products you can see on this shelf."

    print(f"\n[Test] Processing image: {image_path}")
    print(f"[Test] Mode: {'Navigation' if flag == 'low' else 'Identification'}")

    response = await agent.generate(prompt, image_url)
    print(f"\n[Response]\n{response}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # Test mode: process a specific image
        # Usage: python test_gemini.py <image_path> [low|high]
        img_path = sys.argv[1]
        img_flag = sys.argv[2] if len(sys.argv) > 2 else "high"
        asyncio.run(test_single_image(img_path, img_flag))
    else:
        # Default mode: watch for photos
        asyncio.run(main())
