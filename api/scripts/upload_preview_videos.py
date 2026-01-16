#!/usr/bin/env python3
"""Upload preview videos to Cloudflare R2 storage.

This script uploads video files from the iOS PreviewContent directory to R2,
making them available for download by the iOS app in development mode.

Note: Metadata is hardcoded in the API endpoint (routers/preview.py), not stored in R2.
"""

import asyncio
from pathlib import Path

from clients.r2 import R2Client
from config import settings


async def upload_preview_videos() -> None:
    """Upload all preview videos to R2 (without metadata files)."""
    # Find the preview videos directory
    script_dir = Path(__file__).parent.parent.parent
    preview_dir = script_dir / "ios" / "PreviewContent" / "Videos"

    if not preview_dir.exists():
        raise FileNotFoundError(f"Preview directory not found: {preview_dir}")

    # Initialize R2 client
    r2_client = R2Client()

    # Get list of video files
    video_files = sorted(preview_dir.glob("*.mp4"))
    print(f"Found {len(video_files)} video files in {preview_dir}")

    # Upload each video
    for video_path in video_files:
        filename = video_path.name
        print(f"\nUploading {filename}...")

        # Read video file
        with open(video_path, "rb") as f:
            video_data = f.read()

        # Upload video to R2
        r2_key = f"preview/{filename}"
        url = await r2_client.upload_file(
            file_data=video_data, key=r2_key, content_type="video/mp4"
        )
        print(f"  ✓ Uploaded: {url}")

    print(f"\n✓ Successfully uploaded {len(video_files)} videos to R2")
    print(f"\nPublic URL base: {settings.r2_public_url}/preview/")
    print("\nNote: Metadata is hardcoded in routers/preview.py")


if __name__ == "__main__":
    asyncio.run(upload_preview_videos())
