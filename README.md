# Julie

**AI-powered shopping assistant for visually impaired users.**

## The Problem

Grocery shopping is a significant challenge for blind and visually impaired individuals. Identifying products on shelves, reading labels,  and locating specific items typically requires assistance from others—limiting independence and privacy.

## The Solution

Julie combines **Ray-Ban Meta smart glasses** with **AI vision and voice** to give users complete autonomy when shopping, providing them with enough information to make qualitative, subjective choices about product selection. No screen interaction required—everything works through natural voice and audio feedback.

## How It Works

1. **Point** — User faces a shelf wearing the glasses
2. **Scan** — Gemini [via Elevenlabs TTS] guides positioning until the full shelf is visible
3. **Identification** — Gemini identifies all products
4. **Discuss** — User has back and forth conversation with Elevenlabs Agent to determine item selection
5. **Reach** — AI guides their hand directly to the product using real-time camera feedback

The entire experience is **eyes-free**.

## Key Features
- **Voice-first interaction** — No buttons, no screens, just conversation
- **Real-time guidance** — Continuous audio feedback using clock positions ("move to 2 o'clock")
- **Product identification** — Recognizes items, brands, prices, and shelf locations
- **Hand guidance** — Guides user's hand to the exact product location
- **Works with existing hardware** — Ray-Ban Meta glasses + iPhone

## System Architecture

```
                         👓 RAY-BAN META GLASSES
                                  │
                                  │ photos
                                  ▼
                           ┌─────────────┐
                           │   iOS App   │
                           └──────┬──────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
          ▼                       ▼                       ▼
   ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
   │ LOW photos  │        │ HIGH photo  │        │ LOW photos  │
   │ (position)  │        │ (identify)  │        │ (guidance)  │
   └──────┬──────┘        └──────┬──────┘        └──────┬──────┘
          │                      │                      │
          ▼                      ▼                      ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│                           GEMINI VISION AI                                   │
│                                                                              │
│  ① Navigation Mode      ② Identification Mode      ③ Hand Guidance Mode    │
│  "Move camera right"    "Found 12 products"        "Move hand to 2 o'clock" │
│         │                       │                           │               │
│         ▼                       ▼                           ▼               │
│   🔊 TTS Audio            CSV Product List            🔊 TTS Audio          │
└─────────┬───────────────────────┬───────────────────────────┬────────────────┘
          │                       │                           │
          │                       ▼                           │
          │     ┌─────────────────────────────────┐           │
          │     │       FASTAPI BACKEND           │           │
          │     │                                 │           │
          │     │  POST /csv/upload ←── Gemini   │           │
          │     │  GET /csv/get-summary ──→ 11L  │           │
          │     │  POST /user-choice ←── 11L     │◄──────────┘
          │     │  GET /user-choice/latest ──→ Gemini        │
          │     │                                 │           │
          │     └────────────────┬────────────────┘           │
          │                      │                            │
          │                      ▼                            │
          │     ┌─────────────────────────────────┐           │
          │     │  ELEVENLABS CONVERSATIONAL AI   │           │
          │     │                                 │           │
          │     │  🎤 User: "What's available?"   │           │
          │     │  📋 Agent: Reads product list   │           │
          │     │  🎤 User: "I want the Coca Cola"│           │
          │     │  ✅ Agent: Posts choice to API ─┼───────────┘
          │     │                                 │  triggers ③
          │     └─────────────────────────────────┘
          │
          ▼
    🔊 AUDIO OUTPUT (via glasses speakers)
```

**Flow Summary:**
1. **LOW photos** → Gemini guides camera positioning → Audio feedback
2. **HIGH photo** → Gemini identifies products → CSV uploaded to API
3. **ElevenLabs Agent** reads products, user selects via voice → Choice posted to API
4. **LOW photos** → Gemini reads user choice from API → Hand guidance mode → Audio feedback

| Component | Purpose |
|-----------|---------|
| `ios/` | Captures photos from Ray-Ban Meta glasses |
| `agents/` | Gemini AI for vision analysis + ElevenLabs TTS for audio output |
| `api/` | Backend storing product data and user selections |

## Quick Start

```bash
# API
cd api && uv sync && uv run main.py

# Agent
cd agents && uv sync && uv run shelf_assistant.py

# iOS
cd ios && open Blindsighted.xcodeproj
```

**Required API keys** (in `.env` files):
- `GOOGLE_API_KEY` — Gemini vision AI
- `ELEVENLABS_API_KEY` — Voice synthesis

## Accessibility by Design

- **No visual interface required** — All feedback is audio
- **Natural language** — "I want the orange juice" not menu navigation
- **Spatial audio cues** — Clock positions for intuitive direction
- **Confirmation feedback** — "Got it!" when item is reached
- **Error recovery** — Graceful re-prompting if something goes wrong

## License

MIT License — See [LICENSE](LICENSE)
