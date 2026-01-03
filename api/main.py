from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from config import settings
from services.openrouter import openrouter_client
from services.tts import tts_service

app = FastAPI(title="Blindsighted API")

# Configure CORS for Expo app
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class FrameRequest(BaseModel):
    """Request model for frame processing"""

    image: str  # Base64 encoded image
    timestamp: int


class FrameResponse(BaseModel):
    """Response model for frame processing"""

    description: str
    timestamp: int
    processing_time_ms: float


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Blindsighted API", "status": "healthy"}


@app.post("/process-frame", response_model=FrameResponse)
async def process_frame(request: FrameRequest) -> FrameResponse:
    """
    Process a video frame and generate an audio description

    Args:
        request: Frame data with base64 encoded image

    Returns:
        Description and processing metadata
    """
    import time

    start_time = time.time()

    try:
        # Generate description using Gemini via OpenRouter
        description = await openrouter_client.describe_image(request.image)

        # Speak the description
        tts_service.speak(description)

        processing_time = (time.time() - start_time) * 1000

        return FrameResponse(
            description=description,
            timestamp=request.timestamp,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing frame: {str(e)}")
