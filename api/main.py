import base64
from typing import Annotated
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from config import settings
from clients.openrouter import OpenRouterClient
from clients.elevenlabs import ElevenLabsClient

app = FastAPI(title="Blindsighted API")

# Configure CORS for Expo app
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection for clients
def get_openrouter_client() -> OpenRouterClient:
    """Dependency that provides an OpenRouter client instance"""
    return OpenRouterClient()


def get_elevenlabs_client() -> ElevenLabsClient:
    """Dependency that provides an ElevenLabs client instance"""
    return ElevenLabsClient()


class FrameRequest(BaseModel):
    """Request model for frame processing"""

    image: str  # Base64 encoded image
    timestamp: int


class FrameResponse(BaseModel):
    """Response model for frame processing"""

    description: str
    audio: str  # Base64 encoded MP3 audio
    timestamp: int
    processing_time_ms: float


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Blindsighted API", "status": "healthy"}


@app.post("/process-frame", response_model=FrameResponse)
async def process_frame(
    request: FrameRequest,
    openrouter_client: Annotated[OpenRouterClient, Depends(get_openrouter_client)],
    elevenlabs_client: Annotated[ElevenLabsClient, Depends(get_elevenlabs_client)],
) -> FrameResponse:
    """
    Process a video frame and generate an audio description

    Args:
        request: Frame data with base64 encoded image
        openrouter_client: OpenRouter client (injected)
        elevenlabs_client: ElevenLabs client (injected)

    Returns:
        Description and processing metadata
    """
    import time

    start_time = time.time()

    try:
        # Generate description using Gemini via OpenRouter
        description = await openrouter_client.describe_image(request.image)

        # Generate audio using ElevenLabs
        audio_bytes = await elevenlabs_client.text_to_speech(description)
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        processing_time = (time.time() - start_time) * 1000

        return FrameResponse(
            description=description,
            audio=audio_base64,
            timestamp=request.timestamp,
            processing_time_ms=processing_time,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing frame: {str(e)}")
