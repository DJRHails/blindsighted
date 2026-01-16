"""Preview video endpoints for development mode.

Provides endpoints to list and access preview videos stored in R2.
Used by the iOS app to seed development data.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter

from config import settings

router = APIRouter(prefix="/preview", tags=["preview"])

# Hardcoded metadata for preview videos (days ago from current date)
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


@router.get("/videos")
async def list_preview_videos() -> dict[str, list[dict[str, Any]]]:
    """List all available preview videos with their URLs and metadata.

    Returns:
        Dictionary containing list of video objects with filename, URL, and metadata
    """
    videos = []

    for filename, metadata in VIDEO_METADATA.items():
        # Calculate timestamp relative to current time
        now = datetime.now(UTC)
        timestamp = now - timedelta(days=metadata["days_ago"])
        timestamp = timestamp.replace(
            hour=metadata["hour"],
            minute=metadata["minute"],
            second=0,
            microsecond=0,
            tzinfo=UTC,
        )

        videos.append(
            {
                "filename": filename,
                "video_url": f"{settings.r2_public_url}/preview/{filename}",
                "metadata": {
                    "latitude": metadata["latitude"],
                    "longitude": metadata["longitude"],
                    "altitude": 0.0,
                    "heading": metadata["heading"],
                    "speed": 0.0,
                    "timestamp": timestamp.isoformat(),
                },
            }
        )

    return {"videos": videos}
