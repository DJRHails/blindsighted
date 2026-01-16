# Blindsighted Architecture

## Overview

Blindsighted is a real-time vision assistance system for visually impaired users, combining LiveKit WebRTC infrastructure with AI-powered scene description.

## System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         iOS App (Swift)                          │
│  - Meta Ray-Ban Glasses Integration                             │
│  - LiveKit Client (WebRTC)                                       │
│  - Camera/Audio Streaming                                        │
└────────────┬────────────────────────────────────────────────────┘
             │
             │ WebRTC
             │
┌────────────▼────────────────────────────────────────────────────┐
│                    LiveKit Cloud (SFU)                           │
│  - WebRTC Signaling & Media Routing                             │
│  - Room Management                                               │
│  - Track Publishing/Subscribing                                  │
└────────┬────────────────────────────────────┬───────────────────┘
         │                                    │
         │ REST API                           │ Agent Protocol
         │                                    │
┌────────▼─────────────┐            ┌────────▼──────────────────┐
│   FastAPI Backend    │            │   LiveKit Agents          │
│   (api/)             │            │   (agents/)               │
│                      │            │                           │
│ - Session Management │            │ STT-LLM-TTS Pipeline:     │
│ - Room Creation      │            │  - Deepgram (STT)         │
│ - Token Generation   │            │  - Gemini 2.0 (LLM+Vision)│
│ - Database (Postgres)│            │  - ElevenLabs (TTS)       │
│ - R2 Storage         │            │                           │
│ - Agent Metadata     │            │ - Video Frame Buffering   │
└──────────────────────┘            │ - Turn-based Description  │
                                    │ - Self-contained Config   │
                                    └───────────────────────────┘
```

## Data Flow

### 1. Session Initialization
```
iOS App
  │
  ├─> POST /sessions/start (agent_id: optional)
  │   └─> FastAPI creates LiveKit room
  │       └─> Returns: room_name, token, livekit_url
  │
  └─> Connects to LiveKit with token
      └─> Publishes video + audio tracks
```

### 2. Agent Join & Vision Pipeline
```
LiveKit Cloud
  │
  ├─> Agent detects new room
  │   └─> Joins as participant
  │       └─> Subscribes to video track
  │           └─> Buffers latest frame
  │
  └─> User speaks
      │
      ├─> STT: Speech → Text
      │
      ├─> LLM: Text + Video Frame → Response
      │   (Gemini sees what user sees)
      │
      └─> TTS: Response → Speech
          └─> Streamed back to user
```

### 3. Conversation Flow
```
User: "What do you see?"
  │
  ├─> [Video Frame: Kitchen scene]
  │
  ├─> Gemini analyzes frame + text
  │   └─> "I can see a modern kitchen with 
  │        stainless steel appliances..."
  │
  └─> ElevenLabs converts to speech
      └─> Audio streamed to user's glasses
```

## Architecture Patterns

### Separation of Concerns

**API (api/)** - Infrastructure Layer
- Room lifecycle management
- Authentication & authorization
- Session persistence (Postgres)
- Recording storage (R2)
- Exposes REST endpoints
- **Does not contain AI logic**

**Agents (agents/)** - AI Logic Layer
- Self-contained AI workers
- STT-LLM-TTS pipeline configuration
- Video frame processing
- Custom instructions & behavior
- **Independent deployment**
- **User-customizable**

### Agent Customization

Users can:
1. Copy `vision_agent.py`
2. Modify AI models (different LLM, TTS, STT)
3. Change instructions/behavior
4. Add custom processing logic
5. Deploy multiple agents with different configurations

Example custom agent:
```python
# agents/spanish_agent.py
session = AgentSession(
    stt="assemblyai/universal-streaming:es",  # Spanish STT
    llm=openai.LLM(model="gpt-4o"),
    tts=elevenlabs.TTS(voice_id="spanish_voice"),
)
```

### Agent Prefix System

**Session Creation:**
```json
POST /sessions/start
{
  "user_id": "user123",
  "agent_id": "vision-v2"  // Optional custom agent
}
```

**Database:**
```sql
stream_sessions (
  id, room_name, agent_id,  -- Agent identifier
  created_at, status, ...
)
```

**Use Cases:**
- A/B testing different AI models
- User preference (fast vs. detailed)
- Feature flags (experimental features)
- Version rollout (gradual deployment)

### Replay System

**Segments Table:**
```sql
segments (
  session_id, turn_number,
  start_timestamp, end_timestamp,
  video_frame_count, audio_frame_count,
  description,      -- User input
  agent_response,   -- AI output
  recording_id      -- Optional recording reference
)
```

**Replay Flow:**
1. Record conversation as segments
2. Store video frames + transcripts
3. Replay segments with different agent
4. Compare responses
5. Optimize prompts/models

## Technology Stack

### iOS App
- **Language:** Swift 6.2
- **UI:** SwiftUI
- **SDK:** Meta Wearables DAT SDK 0.3.0
- **LiveKit:** LiveKit Swift SDK
- **Target:** iOS 17.0+

### Backend API
- **Runtime:** Python 3.11+
- **Framework:** FastAPI 0.115.6
- **Database:** PostgreSQL (async via psycopg)
- **Migrations:** Alembic 1.14.0
- **Storage:** Cloudflare R2 (S3-compatible)
- **Logging:** Loguru

### LiveKit Agents
- **Framework:** LiveKit Agents 0.12.3
- **STT:** Deepgram Nova 2
- **LLM:** Gemini 2.0 Flash (via OpenRouter)
- **TTS:** ElevenLabs Turbo v2.5
- **VAD:** Silero VAD
- **Vision:** Video frame buffering + multimodal LLM

### Infrastructure
- **WebRTC:** LiveKit Cloud (wss://blindsighted-iogq73td.livekit.cloud)
- **Database:** PostgreSQL on bonbon (65.109.34.215)
- **Storage:** Cloudflare R2 (cdn.blindsighted.hails.info)
- **Deployment:** Docker (API), systemd (Agents)

## LiveKit Integration

### Room Lifecycle

**Create Room:**
```python
# api/services/lk.py
room = await livekit.create_room(room_name)
```

**Generate Token:**
```python
token = livekit.create_access_token(
    room_name=room_name,
    participant_identity=device_id,
)
```

**Start Egress (Recording):**
```python
egress = await livekit.start_room_composite_egress(
    room_name=room_name,
    r2_key=f"recordings/{session_id}/{timestamp}.mp4",
)
```

### Agent Connection

**Agent Server:**
```python
# agents/vision_agent.py
server = AgentServer()

@server.rtc_session()
async def vision_agent(ctx: JobContext):
    session = AgentSession(stt=..., llm=..., tts=...)
    await session.start(room=ctx.room, agent=VisionAssistant())
```

**Automatic Scaling:**
- Agents connect to LiveKit Cloud
- LiveKit routes rooms to available agents
- Multiple agents can run concurrently
- Agents handle multiple rooms

### Video Processing

**Frame Buffering:**
```python
class VisionAssistant(Agent):
    async def on_enter(self):
        # Subscribe to video track
        self._video_stream = rtc.VideoStream(track)
        async for event in self._video_stream:
            self._latest_frame = event.frame  # Buffer latest
    
    async def on_user_turn_completed(self, ctx, message):
        # Attach frame to user message
        if self._latest_frame:
            message.content.append(llm.ChatImage(image=self._latest_frame))
```

**Frame Rate:**
- iOS publishes at 30fps
- Agent buffers latest frame only
- Frame attached once per conversation turn
- No continuous frame processing (cost optimization)

## Database Schema

### stream_sessions
- Room metadata
- Agent configuration (`agent_id`)
- Session lifecycle (created, started, ended)
- User/device tracking

### recordings
- R2 storage references
- Egress metadata
- Duration, file size
- Recording status

### segments
- Conversation turns
- Timestamps per turn
- Frame/audio counts
- AI responses (for replay)

## Security Considerations

### Agent Prefix
- **Not secure by design**
- Anyone can use any `agent_id`
- Agents trust room metadata
- Use for experimentation, not authorization

### API Authentication
- TODO: Add JWT tokens
- TODO: User authentication
- TODO: Rate limiting

### LiveKit Tokens
- Short-lived (1 hour default)
- Room-specific
- Participant-specific
- Can restrict permissions (publish, subscribe)

## Deployment

### API
```bash
cd api
docker build -t blindsighted-api .
docker run -p 8000:8000 --env-file .env blindsighted-api
```

### Agents
```bash
cd agents
uv pip install -e .
uv run python vision_agent.py start
```

### Environment Variables

**API (.env):**
- `DATABASE_URL` - Postgres connection
- `LIVEKIT_*` - LiveKit credentials
- `R2_*` - Cloudflare R2 credentials
- `OPENROUTER_API_KEY` - For REST endpoint
- `ELEVENLABS_API_KEY` - For REST endpoint

**Agents (.env):**
- `LIVEKIT_*` - LiveKit credentials
- `OPENROUTER_API_KEY` - For Gemini LLM
- `ELEVENLABS_API_KEY` - For TTS
- `DEEPGRAM_API_KEY` - For STT

## Future Enhancements

### Planned
- [ ] Segment recording for replay
- [ ] Multi-agent routing by `agent_id`
- [ ] Conversation history UI
- [ ] Real-time transcription display
- [ ] Alternative AI models (GPT-4V, Claude with vision)

### Experimental
- [ ] Gemini Live API (native streaming)
- [ ] Continuous video analysis (not just on turns)
- [ ] Object tracking across frames
- [ ] Spatial audio cues

## Resources

- **LiveKit Docs:** https://docs.livekit.io/
- **LiveKit Agents:** https://docs.livekit.io/agents/
- **Meta Wearables SDK:** https://github.com/facebook/meta-wearables-dat-ios
- **Project Repo:** https://github.com/DJRHails/blindsighted
