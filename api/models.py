"""Database models for Blindsighted"""

from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4
from sqlalchemy import String, DateTime, Integer, Text, Float, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class SessionStatus(str, Enum):
    """Status of a streaming session"""

    CREATED = "created"
    ACTIVE = "active"
    ENDED = "ended"
    FAILED = "failed"


class StreamSession(Base):
    """Model for LiveKit streaming sessions"""

    __tablename__ = "stream_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    room_name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    room_sid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    user_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    status: Mapped[SessionStatus] = mapped_column(
        String(50), nullable=False, default=SessionStatus.CREATED
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    device_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    agent_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    metadata: Mapped[str | None] = mapped_column(Text, nullable=True)


class Recording(Base):
    """Model for session recordings stored in R2"""

    __tablename__ = "recordings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    room_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # R2 storage info
    r2_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    r2_url: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Recording metadata
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    format: Mapped[str] = mapped_column(String(50), nullable=False, default="mp4")

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Egress info
    egress_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")


class Segment(Base):
    """Model for session segments/turns for replay functionality"""

    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    turn_number: Mapped[int] = mapped_column(Integer, nullable=False)

    # Segment timing
    start_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    end_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Segment content
    video_frame_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    audio_frame_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Recording reference (if this segment has a separate recording)
    recording_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Metadata
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )


class User(Base):
    """Model for users who own lifelog entries"""

    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    device_identifier: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    lifelog_entries: Mapped[list["LifelogEntry"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class LifelogEntry(Base):
    """Model for lifelog video entries synced from devices"""

    __tablename__ = "lifelog_entries"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)

    # File identification
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    video_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, unique=True, index=True
    )  # SHA256

    # R2 storage
    r2_key: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    r2_url: Mapped[str] = mapped_column(String(512), nullable=False)

    # Video metadata
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(Float, nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)

    # Location metadata (optional)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    altitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="lifelog_entries")
