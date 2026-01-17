#!/usr/bin/env python3
"""Seed lifelog videos for a user.

This script uploads preview videos from the iOS PreviewContent directory to R2
and stores them in the database as lifelog entries for a specified user.

Usage:
    python seed_lifelog.py <device_identifier>

Example:
    python seed_lifelog.py "my-iphone-13-pro"
"""

import asyncio
import hashlib
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from clients.r2 import R2Client
from config import settings
from models import File, User, LifelogEntry

# Hardcoded metadata for preview videos
VIDEO_METADATA: dict[str, dict[str, Any]] = {
    "market_bazaar.mp4": {
        "days_ago": 1,
        "hour": 14,
        "minute": 30,
        "latitude": 40.7128,
        "longitude": -74.0060,
        "heading": 90.0,
    },
    "park_walk.mp4": {
        "days_ago": 2,
        "hour": 10,
        "minute": 15,
        "latitude": 40.7580,
        "longitude": -73.9855,
        "heading": 180.0,
    },
    "workspace_overhead.mp4": {
        "days_ago": 3,
        "hour": 9,
        "minute": 0,
        "latitude": 37.7749,
        "longitude": -122.4194,
        "heading": 0.0,
    },
    "lanterns.mp4": {
        "days_ago": 4,
        "hour": 19,
        "minute": 45,
        "latitude": 35.6762,
        "longitude": 139.6503,
        "heading": 270.0,
    },
    "city_street_philadelphia.mp4": {
        "days_ago": 5,
        "hour": 15,
        "minute": 20,
        "latitude": 39.9526,
        "longitude": -75.1652,
        "heading": 45.0,
    },
    "city_aerial_sunset.mp4": {
        "days_ago": 6,
        "hour": 18,
        "minute": 30,
        "latitude": 34.0522,
        "longitude": -118.2437,
        "heading": 135.0,
    },
    "boat_seagulls.mp4": {
        "days_ago": 7,
        "hour": 11,
        "minute": 0,
        "latitude": 37.8044,
        "longitude": -122.2712,
        "heading": 225.0,
    },
    "underwater_manta_rays.mp4": {
        "days_ago": 8,
        "hour": 13,
        "minute": 45,
        "latitude": 21.3099,
        "longitude": -157.8581,
        "heading": 315.0,
    },
    "scuba_diving_fish_school.mp4": {
        "days_ago": 9,
        "hour": 14,
        "minute": 15,
        "latitude": 18.2208,
        "longitude": -63.0686,
        "heading": 60.0,
    },
    "sea_turtle_dive.mp4": {
        "days_ago": 10,
        "hour": 12,
        "minute": 30,
        "latitude": 20.7984,
        "longitude": -156.3319,
        "heading": 120.0,
    },
    "desert_sunset.mp4": {
        "days_ago": 11,
        "hour": 17,
        "minute": 0,
        "latitude": 36.1147,
        "longitude": -115.1728,
        "heading": 240.0,
    },
    "monkey_jungle.mp4": {
        "days_ago": 12,
        "hour": 10,
        "minute": 45,
        "latitude": 10.7769,
        "longitude": 106.7009,
        "heading": 90.0,
    },
    "proposal.mp4": {
        "days_ago": 13,
        "hour": 16,
        "minute": 0,
        "latitude": 48.8566,
        "longitude": 2.3522,
        "heading": 180.0,
    },
    "monkey_jungle_2.mp4": {
        "days_ago": 14,
        "hour": 11,
        "minute": 20,
        "latitude": 10.7769,
        "longitude": 106.7009,
        "heading": 270.0,
    },
}


def calculate_video_hash(video_path: Path) -> str:
    """Calculate SHA256 hash of video file."""
    sha256_hash = hashlib.sha256()
    with open(video_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()


def get_video_duration(video_path: Path) -> float:
    """Get video duration in seconds.

    For preview videos, we use hardcoded durations.
    For real sync, the iOS app will provide actual duration.
    """
    # Hardcoded approximate durations for preview videos (in seconds)
    durations = {
        "market_bazaar.mp4": 30.0,
        "park_walk.mp4": 45.0,
        "workspace_overhead.mp4": 25.0,
        "lanterns.mp4": 35.0,
        "city_street_philadelphia.mp4": 40.0,
        "city_aerial_sunset.mp4": 50.0,
        "boat_seagulls.mp4": 30.0,
        "underwater_manta_rays.mp4": 55.0,
        "scuba_diving_fish_school.mp4": 42.0,
        "sea_turtle_dive.mp4": 38.0,
        "desert_sunset.mp4": 45.0,
        "monkey_jungle.mp4": 32.0,
        "proposal.mp4": 60.0,
        "monkey_jungle_2.mp4": 28.0,
    }
    return durations.get(video_path.name, 30.0)


async def get_or_create_user(session: AsyncSession, device_identifier: str) -> User:
    """Get existing user or create new one."""
    result = await session.execute(select(User).where(User.device_identifier == device_identifier))
    user = result.scalar_one_or_none()

    if user:
        print(f"Found existing user: {user.id}")
    else:
        user = User(device_identifier=device_identifier)
        session.add(user)
        await session.flush()
        print(f"Created new user: {user.id}")

    return user


async def seed_lifelog(device_identifier: str) -> None:
    """Seed lifelog videos for a user."""
    # Find the preview videos directory
    script_dir = Path(__file__).parent.parent.parent
    preview_dir = script_dir / "ios" / "PreviewContent" / "Videos"

    if not preview_dir.exists():
        raise FileNotFoundError(f"Preview directory not found: {preview_dir}")

    # Initialize R2 client
    r2_client = R2Client()

    # Setup async database connection
    # Convert sync URL to async (postgresql+psycopg -> postgresql+psycopg)
    async_url = settings.database_url.replace("postgresql+psycopg://", "postgresql+psycopg://")
    engine = create_async_engine(async_url, echo=False)
    async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session_maker() as session:
        # Get or create user
        user = await get_or_create_user(session, device_identifier)

        # Get list of video files
        video_files = sorted(preview_dir.glob("*.mp4"))
        print(f"\nFound {len(video_files)} video files in {preview_dir}")

        # Upload each video
        for video_path in video_files:
            filename = video_path.name
            print(f"\nProcessing {filename}...")

            # Calculate content hash
            content_hash = calculate_video_hash(video_path)
            print(f"  Hash: {content_hash[:16]}...")

            # Check if file already exists (globally)
            result = await session.execute(select(File).where(File.content_hash == content_hash))
            file = result.scalar_one_or_none()

            # If file doesn't exist, create it
            if not file:
                # Read video file
                with open(video_path, "rb") as f:
                    video_data = f.read()

                file_size = len(video_data)

                # Get video duration
                duration = get_video_duration(video_path)
                print(f"  Duration: {duration:.2f}s, Size: {file_size / 1024 / 1024:.2f} MB")

                # Upload video to object storage
                storage_key = f"lifelog/{content_hash[:8]}/{filename}"
                storage_url = await r2_client.upload_file(
                    file_data=video_data, key=storage_key, content_type="video/mp4"
                )
                print(f"  ✓ Uploaded to storage: {storage_url}")

                # Create file entry
                file = File(
                    content_hash=content_hash,
                    content_type="video/mp4",
                    storage_key=storage_key,
                    storage_url=storage_url,
                    file_size_bytes=file_size,
                    duration_seconds=duration,
                )
                session.add(file)
                await session.flush()
                print(f"  ✓ Created file entry: {file.id}")
            else:
                print(f"  ✓ File already exists (ID: {file.id}), reusing")

            # Check if this user already has a lifelog entry for this file
            result = await session.execute(
                select(LifelogEntry).where(
                    LifelogEntry.user_id == user.id, LifelogEntry.file_id == file.id
                )
            )
            existing_entry = result.scalar_one_or_none()

            if existing_entry:
                print(f"  ⚠ Lifelog entry already exists for this user (ID: {existing_entry.id}), skipping")
                continue

            # Get metadata
            metadata = VIDEO_METADATA.get(filename, {})

            # Calculate timestamp
            if metadata:
                now = datetime.now(UTC)
                recorded_at = now - timedelta(days=metadata["days_ago"])
                recorded_at = recorded_at.replace(
                    hour=metadata["hour"],
                    minute=metadata["minute"],
                    second=0,
                    microsecond=0,
                    tzinfo=UTC,
                )
            else:
                # Default to now if no metadata
                recorded_at = datetime.now(UTC)

            # Create lifelog entry
            entry = LifelogEntry(
                user_id=user.id,
                file_id=file.id,
                filename=filename,
                recorded_at=recorded_at,
                latitude=metadata.get("latitude"),
                longitude=metadata.get("longitude"),
                altitude=0.0 if metadata else None,
                heading=metadata.get("heading"),
                speed=0.0 if metadata else None,
            )

            session.add(entry)
            await session.flush()
            print(f"  ✓ Created lifelog entry: {entry.id}")

        # Update user's last sync time
        user.last_sync_at = datetime.now(UTC)
        await session.commit()

        print(f"\n✅ Successfully seeded {len(video_files)} videos for user {device_identifier}")


async def main() -> None:
    """Main entry point."""
    if len(sys.argv) != 2:
        print("Usage: python seed_lifelog.py <device_identifier>")
        print('Example: python seed_lifelog.py "my-iphone-13-pro"')
        sys.exit(1)

    device_identifier = sys.argv[1]
    print(f"Seeding lifelog for device: {device_identifier}")

    await seed_lifelog(device_identifier)


if __name__ == "__main__":
    asyncio.run(main())
