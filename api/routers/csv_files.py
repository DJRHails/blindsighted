"""API routes for CSV file management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import CSVFile

router = APIRouter(prefix="/csv", tags=["csv"])


class CSVFileResponse(BaseModel):
    """Response model for CSV file data."""

    id: str
    filename: str
    content: str
    file_size_bytes: int
    created_at: str
    updated_at: str


@router.get("/get-summary", response_model=CSVFileResponse)
async def get_summary(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CSVFileResponse:
    """Get the latest CSV file from the database.
    
    Returns the most recently created CSV file based on created_at timestamp.
    """
    # Query for the latest CSV file ordered by created_at descending
    result = await db.execute(
        select(CSVFile).order_by(desc(CSVFile.created_at)).limit(1)
    )
    csv_file = result.scalar_one_or_none()
    
    if not csv_file:
        raise HTTPException(
            status_code=404, 
            detail="No CSV files found in the database"
        )
    
    return CSVFileResponse(
        id=str(csv_file.id),
        filename=csv_file.filename,
        content=csv_file.file_content,
        file_size_bytes=csv_file.file_size_bytes,
        created_at=csv_file.created_at.isoformat(),
        updated_at=csv_file.updated_at.isoformat(),
    )


@router.post("/upload")
async def upload_csv(
    file: Annotated[UploadFile, File()],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, str]:
    """Upload a CSV file to the database.
    
    Args:
        file: CSV file to upload
        db: Database session
    """
    # Read file content
    content = await file.read()
    content_str = content.decode('utf-8')
    
    if not content_str:
        raise HTTPException(
            status_code=400,
            detail="File content is empty"
        )
    
    # Create new CSV file record
    csv_file = CSVFile(
        filename=file.filename or "uploaded.csv",
        file_content=content_str,
        file_size_bytes=len(content),
    )
    
    db.add(csv_file)
    await db.commit()
    await db.refresh(csv_file)
    
    return {
        "message": "CSV file uploaded successfully",
        "id": str(csv_file.id),
        "filename": csv_file.filename,
    }
