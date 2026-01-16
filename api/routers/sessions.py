"""API routes for streaming session management."""

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import UTC, datetime

from database import get_db
from models import StreamSession, SessionStatus
from services.lk import LiveKitService


router = APIRouter(prefix="/sessions", tags=["sessions"])


class StartSessionRequest(BaseModel):
    """Request to start a new streaming session."""

    user_id: str | None = None
    device_id: str | None = None
    agent_id: str | None = None  # Custom agent prefix for this session


class StartSessionResponse(BaseModel):
    """Response after starting a session."""

    session_id: int
    room_name: str
    token: str
    livekit_url: str


class StopSessionRequest(BaseModel):
    """Request to stop a streaming session."""

    session_id: int


def get_livekit_service() -> LiveKitService:
    """Dependency for LiveKit service."""
    return LiveKitService()


@router.post("/start", response_model=StartSessionResponse)
async def start_session(
    request: StartSessionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    livekit: Annotated[LiveKitService, Depends(get_livekit_service)],
) -> StartSessionResponse:
    """Start a new streaming session with LiveKit.

    Creates a room, generates an access token, and optionally starts recording.
    """
    try:
        # Generate unique room name
        room_name = livekit.generate_room_name()

        # Create LiveKit room
        room = await livekit.create_room(room_name)

        # Create database session record
        session = StreamSession(
            room_name=room_name,
            room_sid=room.sid,
            user_id=request.user_id,
            device_id=request.device_id,
            agent_id=request.agent_id,
            status=SessionStatus.CREATED,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

        # Generate access token for client
        participant_identity = request.device_id or f"user-{session.id}"
        token = livekit.create_access_token(
            room_name=room_name,
            participant_identity=participant_identity,
            participant_name=request.user_id,
        )

        return StartSessionResponse(
            session_id=session.id,
            room_name=room_name,
            token=token,
            livekit_url=livekit.url,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to start session: {str(e)}")


@router.post("/stop")
async def stop_session(
    request: StopSessionRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    livekit: Annotated[LiveKitService, Depends(get_livekit_service)],
) -> dict[str, str]:
    """Stop an active streaming session."""
    try:
        # Get session from database
        result = await db.execute(
            select(StreamSession).where(StreamSession.id == request.session_id)
        )
        session = result.scalar_one_or_none()

        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        if session.status == SessionStatus.ENDED:
            return {"message": "Session already ended"}

        # Update session status
        session.status = SessionStatus.ENDED
        session.ended_at = datetime.now(UTC)
        await db.commit()

        # Delete LiveKit room
        try:
            await livekit.delete_room(session.room_name)
        except Exception as e:
            # Log error but don't fail the request
            print(f"Failed to delete room: {e}")

        return {"message": "Session stopped successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to stop session: {str(e)}")


@router.get("/{session_id}")
async def get_session(
    session_id: int,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get session details."""
    result = await db.execute(select(StreamSession).where(StreamSession.id == session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "id": session.id,
        "room_name": session.room_name,
        "room_sid": session.room_sid,
        "user_id": session.user_id,
        "device_id": session.device_id,
        "agent_id": session.agent_id,
        "status": session.status,
        "created_at": session.created_at.isoformat(),
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
    }
