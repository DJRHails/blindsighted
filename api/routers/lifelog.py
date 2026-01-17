"""Lifelog sync endpoints.

Provides endpoints for syncing lifelog video entries between devices and cloud storage.
"""

import hashlib
from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from loguru import logger
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from clients.r2 import R2Client
from database import get_db
from models import File, LifelogEntry, User

router = APIRouter(prefix="/lifelog", tags=["lifelog"])


# Request/Response models
class LifelogEntryResponse(BaseModel):
    """Response model for a lifelog entry."""

    id: UUID
    filename: str
    video_hash: str
    r2_url: str
    recorded_at: datetime
    duration_seconds: float
    file_size_bytes: int
    latitude: float | None
    longitude: float | None
    altitude: float | None
    heading: float | None
    speed: float | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SyncResponse(BaseModel):
    """Response for sync request."""

    entries: list[LifelogEntryResponse]
    total_count: int
    last_sync_at: datetime | None


class UploadResponse(BaseModel):
    """Response for upload request."""

    id: str
    video_hash: str
    r2_url: str
    already_exists: bool


# Dependency injection
def get_r2_client() -> R2Client:
    """Dependency that provides an R2 client instance."""
    return R2Client()


async def get_or_create_user(device_identifier: str, db: AsyncSession) -> User:
    """Get existing user or create new one."""
    result = await db.execute(select(User).where(User.device_identifier == device_identifier))
    user = result.scalar_one_or_none()

    if not user:
        user = User(device_identifier=device_identifier)
        db.add(user)
        await db.flush()

    return user


@router.get("/sync/{device_identifier}", response_model=SyncResponse)
async def sync_lifelog(
    device_identifier: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SyncResponse:
    """Get all lifelog entries for a device/user.

    Args:
        device_identifier: Unique device identifier (e.g., iOS device UUID)
        db: Database session

    Returns:
        List of lifelog entries and sync metadata
    """
    # Get or create user
    user = await get_or_create_user(device_identifier, db)

    # Get all entries for user with file data
    result = await db.execute(
        select(LifelogEntry, File)
        .join(File, LifelogEntry.file_id == File.id)
        .where(LifelogEntry.user_id == user.id)
        .order_by(LifelogEntry.recorded_at.desc())
    )
    rows = result.all()

    logger.info(f"Found {len(rows)} entries for user {user.id}")

    # Update last sync time
    user.last_sync_at = datetime.now(UTC)
    await db.commit()

    # Construct response with file data
    entries = [
        LifelogEntryResponse(
            id=entry.id,
            filename=entry.filename,
            video_hash=file.content_hash,
            r2_url=file.storage_url,
            recorded_at=entry.recorded_at,
            duration_seconds=file.duration_seconds or 0.0,
            file_size_bytes=file.file_size_bytes,
            latitude=entry.latitude,
            longitude=entry.longitude,
            altitude=entry.altitude,
            heading=entry.heading,
            speed=entry.speed,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )
        for entry, file in rows
    ]

    return SyncResponse(
        entries=entries,
        total_count=len(entries),
        last_sync_at=user.last_sync_at,
    )


@router.post("/upload/{device_identifier}", response_model=UploadResponse)
async def upload_video(
    device_identifier: str,
    video: Annotated[UploadFile, File()],
    filename: Annotated[str, Form()],
    recorded_at: Annotated[str, Form()],  # ISO8601 datetime string
    duration_seconds: Annotated[float, Form()],
    latitude: Annotated[float | None, Form()] = None,
    longitude: Annotated[float | None, Form()] = None,
    altitude: Annotated[float | None, Form()] = None,
    heading: Annotated[float | None, Form()] = None,
    speed: Annotated[float | None, Form()] = None,
    *,
    db: Annotated[AsyncSession, Depends(get_db)],
    r2_client: Annotated[R2Client, Depends(get_r2_client)],
) -> UploadResponse:
    """Upload a new lifelog video.

    Args:
        device_identifier: Unique device identifier
        video: Video file to upload
        filename: Original filename
        recorded_at: ISO8601 timestamp when video was recorded
        duration_seconds: Video duration in seconds
        latitude: GPS latitude (optional)
        longitude: GPS longitude (optional)
        altitude: GPS altitude (optional)
        heading: Compass heading (optional)
        speed: Speed in m/s (optional)
        db: Database session
        r2_client: R2 storage client

    Returns:
        Upload response with entry ID and hash
    """
    # Get or create user
    user = await get_or_create_user(device_identifier, db)

    # Read video data
    video_data = await video.read()
    file_size = len(video_data)

    # Calculate content hash
    content_hash = hashlib.sha256(video_data).hexdigest()

    # Check if file already exists (globally)
    result = await db.execute(select(File).where(File.content_hash == content_hash))
    file = result.scalar_one_or_none()

    # If file doesn't exist, create it
    if not file:
        # Upload to object storage
        storage_key = f"lifelog/{content_hash[:8]}/{filename}"
        storage_url = await r2_client.upload_file(
            file_data=video_data, key=storage_key, content_type="video/mp4"
        )

        # Create file entry
        file = File(
            content_hash=content_hash,
            content_type="video/mp4",
            storage_key=storage_key,
            storage_url=storage_url,
            file_size_bytes=file_size,
            duration_seconds=duration_seconds,
        )
        db.add(file)
        await db.flush()  # Get file.id

    # Check if this user already has a lifelog entry for this file
    result = await db.execute(
        select(LifelogEntry).where(
            LifelogEntry.user_id == user.id, LifelogEntry.file_id == file.id
        )
    )
    existing_entry = result.scalar_one_or_none()

    if existing_entry:
        await db.commit()
        return UploadResponse(
            id=str(existing_entry.id),
            video_hash=file.content_hash,
            r2_url=file.storage_url,
            already_exists=True,
        )

    # Parse recorded_at timestamp
    recorded_at_dt = datetime.fromisoformat(recorded_at.replace("Z", "+00:00"))

    # Create lifelog entry
    entry = LifelogEntry(
        user_id=user.id,
        file_id=file.id,
        filename=filename,
        recorded_at=recorded_at_dt,
        latitude=latitude,
        longitude=longitude,
        altitude=altitude,
        heading=heading,
        speed=speed,
    )

    db.add(entry)
    await db.commit()
    await db.refresh(entry)

    return UploadResponse(
        id=str(entry.id),
        video_hash=file.content_hash,
        r2_url=file.storage_url,
        already_exists=False,
    )


@router.delete("/{device_identifier}/{entry_id}")
async def delete_entry(
    device_identifier: str,
    entry_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    r2_client: Annotated[R2Client, Depends(get_r2_client)],
) -> dict[str, str]:
    """Delete a lifelog entry.

    Args:
        device_identifier: Unique device identifier
        entry_id: Entry ID to delete
        db: Database session
        r2_client: R2 storage client

    Returns:
        Success message
    """
    # Get user
    user = await get_or_create_user(device_identifier, db)

    # Get entry with file
    result = await db.execute(
        select(LifelogEntry, File)
        .join(File, LifelogEntry.file_id == File.id)
        .where(LifelogEntry.id == entry_id, LifelogEntry.user_id == user.id)
    )
    row = result.one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")

    entry, file = row

    # Delete entry from database
    await db.delete(entry)
    await db.flush()

    # Check if any other lifelog entries reference this file
    result = await db.execute(
        select(LifelogEntry).where(LifelogEntry.file_id == file.id).limit(1)
    )
    other_entry = result.scalar_one_or_none()

    # If no other entries reference this file, delete it from storage and database
    if not other_entry:
        try:
            await r2_client.delete_file(file.storage_key)
        except Exception as e:
            # Log error but continue with database deletion
            logger.warning(f"Failed to delete file from storage: {e}")

        await db.delete(file)

    await db.commit()

    return {"message": "Entry deleted successfully"}
