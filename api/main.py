import base64
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from clients.elevenlabs import ElevenLabsClient
from clients.openrouter import OpenRouterClient
from config import settings
from routers import lifelog, photos, preview, sessions


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan manager."""
    # Startup: database migrations are handled by Alembic
    yield
    # Shutdown: cleanup if needed


app = FastAPI(title="Blindsighted API", lifespan=lifespan)

# Configure CORS for Expo app
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(sessions.router)
app.include_router(preview.router)
app.include_router(lifelog.router)
app.include_router(photos.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Blindsighted API", "status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.getenv("BLINDSIGHTED_API_PORT", 9999)),
        reload=True,
    )
