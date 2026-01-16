# Blindsighted API

FastAPI backend for the Blindsighted app with AI-powered visual assistance.

## Features

- **Frame Processing**: Receives video frames from Meta AI Glasses
- **AI Vision**: Uses Gemini (via OpenRouter) to describe scenes
- **Text-to-Speech**: Converts descriptions to audio for blind/visually impaired users
- **Real-time Streaming**: Processes frames at configurable FPS

## Setup

### 1. Install Dependencies

Install dependencies using uv:
```bash
uv pip install -e ".[dev]"
```

Or install just the production dependencies:
```bash
uv pip install -e .
```

### 2. Configure Environment

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your OpenRouter API key:
```bash
OPENROUTER_API_KEY=your_api_key_here
```

Get an API key from [OpenRouter](https://openrouter.ai/)

## Development

Format and lint code:
```bash
ruff check --fix .
ruff format .
```

Type check:
```bash
ty .
```

## Running the API

Start the development server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- **API**: `http://localhost:8000`
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

## API Endpoints

### `POST /process-frame`

Process a video frame and generate an audio description.

**Request:**
```json
{
  "image": "base64_encoded_image_string",
  "timestamp": 1704300000000
}
```

**Response:**
```json
{
  "description": "You are looking at a street scene with cars and pedestrians...",
  "timestamp": 1704300000000,
  "processing_time_ms": 1234.5
}
```

## How It Works

1. **App captures frame**: Meta AI Glasses capture a photo every 2 seconds (configurable)
2. **Frame sent to API**: Base64 encoded image sent to `/process-frame`
3. **Gemini vision analysis**: OpenRouter routes request to Gemini 2.0 Flash for image description
4. **Audio generation**: Description converted to speech using pyttsx3
5. **Real-time playback**: Audio played immediately to assist the user
