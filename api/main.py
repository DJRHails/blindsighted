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
from routers import csv_files, lifelog, photos, preview, user_choice


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
app.include_router(user_choice.router)
app.include_router(preview.router)
app.include_router(lifelog.router)
app.include_router(photos.router)
app.include_router(csv_files.router)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Blindsighted API", "status": "healthy"}


if __name__ == "__main__":
    import uvicorn

    # SSL certificate paths for HTTPS
    ssl_keyfile = os.getenv("SSL_KEYFILE", "localhost-key.pem")
    ssl_certfile = os.getenv("SSL_CERTFILE", "localhost.pem")
    
    # Check if SSL certificates exist
    has_ssl = os.path.exists(ssl_keyfile) and os.path.exists(ssl_certfile)
    
    if has_ssl:
        print(f"HTTPS enabled with certificates: {ssl_certfile}, {ssl_keyfile}")
    else:
        print(f"Warning: SSL certificates not found. Running HTTP only.")
        print(f"Expected files: {ssl_keyfile}, {ssl_certfile}")
        print("Generate certificates using: openssl req -x509 -newkey rsa:4096 -keyout localhost-key.pem -out localhost.pem -days 365 -nodes")

    port = int(os.getenv("BLINDSIGHTED_API_PORT", 8000))
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        ssl_keyfile=ssl_keyfile if has_ssl else None,
        ssl_certfile=ssl_certfile if has_ssl else None,
    )
