"""Photo analysis endpoints for grocery shelf scanning.

Routes photos to appropriate Gemini instance based on flag:
- LOW: Navigation/positioning guidance
- HIGH: Item identification and listing
"""

from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from clients.gemini import GeminiClient

router = APIRouter(prefix="/photos", tags=["photos"])


class PhotoFlag(str, Enum):
    """Flag indicating the type of photo analysis needed."""

    LOW = "low"  # Navigation mode - guide user positioning
    HIGH = "high"  # Identification mode - list shelf items


class PhotoAnalysisRequest(BaseModel):
    """Request to analyze a photo."""

    image_base64: str  # Base64 encoded JPEG image
    flag: PhotoFlag  # Analysis type


class PhotoAnalysisResponse(BaseModel):
    """Response from photo analysis."""

    response: str  # Gemini's text response
    flag: PhotoFlag  # Echo back the flag used


# System prompts for each mode
NAVIGATION_PROMPT = """You are helping a blind user position themselves in front of a grocery shelf.
Analyze the image and provide positioning instructions.

If you can see a clear, full view of a shelf section, respond with:
"READY: [brief description of what you see]"

Otherwise, give brief, actionable instructions:
- "move left" - if shelf extends to the right out of view
- "move right" - if shelf extends to the left out of view
- "step back" - if too close to see full shelf
- "step forward" - if too far away
- "tilt up" or "tilt down" - if viewing angle needs adjustment

Be concise. One instruction at a time."""

IDENTIFICATION_PROMPT = """You are helping a blind user identify items on a grocery shelf.
List all visible products clearly and concisely.

For each item include:
- Product name and brand (if visible)
- Position: left/center/right, top/middle/bottom shelf
- Size or quantity if visible

Format as a numbered list. Be thorough but concise."""


@router.post("/analyze", response_model=PhotoAnalysisResponse)
async def analyze_photo(request: PhotoAnalysisRequest) -> PhotoAnalysisResponse:
    """Analyze a photo using the appropriate Gemini instance based on flag.

    Args:
        request: Contains base64 image and flag (low/high)

    Returns:
        Gemini's analysis response
    """
    gemini = GeminiClient()

    # Select prompt based on flag
    if request.flag == PhotoFlag.LOW:
        prompt = NAVIGATION_PROMPT
    else:
        prompt = IDENTIFICATION_PROMPT

    try:
        response = await gemini.analyze_image(
            image_base64=request.image_base64,
            prompt=prompt,
        )

        return PhotoAnalysisResponse(
            response=response,
            flag=request.flag,
        )
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gemini API error: {str(e)}")
