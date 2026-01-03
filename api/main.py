from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Blindsighted API")

# Configure CORS for Expo app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure this based on your environment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    return {"message": "Welcome to Blindsighted API", "status": "healthy"}
