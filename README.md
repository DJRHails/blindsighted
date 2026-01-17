# Blindsighted

**AI-powered shopping assistant for visually impaired users to select items from supermarket shelves.**

Blindsighted uses Gemini vision AI to analyze store shelves and ElevenLabs conversational AI to help users select and locate products through voice interaction.

## Architecture Overview

```
iOS App (Camera) → Photos Directory → Gemini Agent → FastAPI Backend
                                           ↓
                              ElevenLabs Voice Agent ← User Voice
                                           ↓
                              Gemini Agent (Hand Guidance)
```

**Three components:**

- **`agents/`** - Gemini-powered shelf assistant (Python)
  - Watches for photos from the iOS app
  - Guides camera positioning (LOW flag photos)
  - Identifies products and generates CSV (HIGH flag photos)
  - Guides user's hand to selected item

- **`api/`** - FastAPI backend (Python)
  - Stores product CSV data
  - Receives user choice from ElevenLabs
  - Provides endpoints for the complete flow

- **`ios/`** - iOS app for Ray-Ban Meta glasses (Swift)
  - Captures photos from smart glasses camera
  - Saves photos with LOW/HIGH flags to Documents folder

## User Flow

1. **Camera Positioning** - User points glasses at shelf, Gemini guides them until full shelf is visible
2. **Product Identification** - HIGH quality photo captured, Gemini lists all products as CSV
3. **Voice Selection** - ElevenLabs agent reads products, user selects one via voice
4. **Hand Guidance** - Gemini guides user's hand to the selected item using new LOW photos

## Quick Start

### API Backend

```bash
cd api
uv sync
uv run alembic upgrade head  # Run database migrations
uv run main.py               # Start API server on port 8000
```

API docs available at `http://localhost:8000/docs`

### Gemini Agent

```bash
cd agents
uv sync
uv run shelf_assistant.py    # Start watching for photos
```

**Required environment variables** (in `agents/.env`):
```
GOOGLE_API_KEY=your_gemini_api_key
API_BASE_URL=http://localhost:8000
```

### iOS App

```bash
cd ios
open Blindsighted.xcodeproj  # Open in Xcode, build and run
```

## API Endpoints

### ElevenLabs Integration

**Store user's item selection:**
```
POST http://localhost:8000/user-choice

Request Body:
{
    "item_name": "Coca Cola 330ml",
    "item_location": "middle shelf, center"  // optional
}

Response:
{
    "message": "Choice recorded",
    "id": "uuid-here"
}
```

**Get available products (CSV):**
```
GET http://localhost:8000/csv/get-summary

Response:
{
    "id": "uuid",
    "filename": "shelf_items_20260117.csv",
    "content": "item_number,product_name,brand,location,price\n1,Cola,Coca-Cola,top shelf,1.99\n...",
    "file_size_bytes": 1234,
    "created_at": "2026-01-17T12:00:00Z",
    "updated_at": "2026-01-17T12:00:00Z"
}
```

### Other Endpoints

- `GET /user-choice/latest` - Get latest unprocessed user choice
- `PATCH /user-choice/{id}/processed` - Mark choice as processed
- `POST /csv/upload` - Upload CSV file (used by Gemini agent)

## ElevenLabs Agent Setup

1. Create a Conversational AI agent at [elevenlabs.io](https://elevenlabs.io)
2. Agent ID: `agent_0701kf5rm5s6f7jtnh7swk9nkx0a`
3. Configure the agent to:
   - Call `GET /csv/get-summary` to read available products
   - Parse CSV and present options to user via voice
   - Call `POST /user-choice` with the user's selection

## Photo Naming Convention

Photos must include a flag in the filename:

- `photo_2026-01-17T12-00-00_low.jpg` - Navigation/guidance mode
- `photo_2026-01-17T12-00-00_high.jpg` - Product identification mode

The Gemini agent watches `~/Documents/BlindsightedPhotos/` for new files.

## Environment Variables

### API (`api/.env`)
```
DATABASE_URL=postgresql://localhost/blindsighted
GOOGLE_API_KEY=your_key
ELEVENLABS_API_KEY=your_key
```

### Agents (`agents/.env`)
```
GOOGLE_API_KEY=your_gemini_api_key
API_BASE_URL=http://localhost:8000
ELEVENLABS_API_KEY=your_key
ELEVENLABS_AGENT_ID=agent_0701kf5rm5s6f7jtnh7swk9nkx0a
```

## Development

### Running Tests
```bash
cd api
uv run ruff check .  # Lint
uv run ruff format . # Format
```

### Database Migrations
```bash
cd api
uv run alembic upgrade head     # Apply migrations
uv run alembic revision --autogenerate -m "Description"  # Create migration
```

## License

MIT License - See [LICENSE](LICENSE) for details.
