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
mypy .
```

## Running the API

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

API documentation available at `http://localhost:8000/docs`
