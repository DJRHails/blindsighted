"""API routes for user choice management (ElevenLabs integration)."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import UserChoice, CSVFile

router = APIRouter(prefix="/user-choice", tags=["user-choice"])


class UserChoiceRequest(BaseModel):
    """Request body for storing user's item selection."""

    item_name: str
    item_location: str | None = None


class UserChoiceResponse(BaseModel):
    """Response after storing user's choice."""

    message: str
    id: str


class UserChoiceDetail(BaseModel):
    """Detailed user choice response."""

    id: str
    item_name: str
    item_location: str | None
    processed: bool
    created_at: str


@router.post("", response_model=UserChoiceResponse)
async def create_user_choice(
    request: UserChoiceRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> UserChoiceResponse:
    """Store the user's selected item from ElevenLabs voice call.

    This endpoint is called by the ElevenLabs agent when the user
    has selected an item they want to find on the shelf.
    """
    # Get the latest CSV file ID (optional association)
    csv_result = await db.execute(
        select(CSVFile).order_by(desc(CSVFile.created_at)).limit(1)
    )
    latest_csv = csv_result.scalar_one_or_none()

    # Create the user choice record
    user_choice = UserChoice(
        item_name=request.item_name,
        item_location=request.item_location,
        csv_file_id=latest_csv.id if latest_csv else None,
        processed=False,
    )

    db.add(user_choice)
    await db.commit()
    await db.refresh(user_choice)

    return UserChoiceResponse(
        message="Choice recorded",
        id=str(user_choice.id),
    )


@router.get("/latest", response_model=UserChoiceDetail | None)
async def get_latest_user_choice(
    db: Annotated[AsyncSession, Depends(get_db)],
    unprocessed_only: bool = True,
) -> UserChoiceDetail | None:
    """Get the latest user choice.

    Args:
        unprocessed_only: If True (default), only return unprocessed choices.
                         Set to False to get the latest choice regardless of status.

    Returns:
        The latest user choice, or None if no choices exist.
    """
    query = select(UserChoice).order_by(desc(UserChoice.created_at))

    if unprocessed_only:
        query = query.where(UserChoice.processed == False)  # noqa: E712

    query = query.limit(1)
    result = await db.execute(query)
    user_choice = result.scalar_one_or_none()

    if not user_choice:
        return None

    return UserChoiceDetail(
        id=str(user_choice.id),
        item_name=user_choice.item_name,
        item_location=user_choice.item_location,
        processed=user_choice.processed,
        created_at=user_choice.created_at.isoformat(),
    )


@router.patch("/{choice_id}/processed")
async def mark_choice_processed(
    choice_id: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Mark a user choice as processed.

    Called by the Gemini agent after it has guided the user to the item.
    """
    result = await db.execute(
        select(UserChoice).where(UserChoice.id == choice_id)
    )
    user_choice = result.scalar_one_or_none()

    if not user_choice:
        raise HTTPException(status_code=404, detail="User choice not found")

    user_choice.processed = True
    await db.commit()

    return {"message": "Choice marked as processed"}
