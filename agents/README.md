# Blindsighted Agents

Self-contained LiveKit agents for vision-based AI assistance. Users can customize these agents with their own AI models and logic.

## Architecture

This directory contains **self-contained agents** that are separate from the API:

- **`api/`** - Infrastructure (room management, tokens, database)
- **`agents/`** - Custom AI logic (STT, LLM, TTS, vision processing)

Users can run the API once and deploy multiple different agent workers with custom configurations.

## Vision Agent

The vision agent uses a streaming STT-LLM-TTS pipeline with video frame analysis:

**Pipeline:**
1. **STT** (Deepgram) - Converts user speech to text
2. **LLM** (Gemini 2.0 Flash) - Processes text + video frames, generates responses
3. **TTS** (ElevenLabs) - Converts responses to natural speech

**Vision Integration:**
- Buffers the latest video frame from user's camera
- Attaches frame to each conversation turn
- LLM can see what the user sees and describe the environment

## Setup

### 1. Install Dependencies

```bash
cd agents
uv pip install -e .
```

### 2. Configure Environment

Copy `.env.example` to `.env` and add your API keys:

```bash
cp .env.example .env
```

Required API keys:
- **LiveKit** - Already configured (from API setup)
- **OpenRouter** - Get from https://openrouter.ai/
- **ElevenLabs** - Get from https://elevenlabs.io/
- **Deepgram** - Get from https://deepgram.com/

### 3. Run the Agent

```bash
# Development mode
uv run python vision_agent.py dev

# Production mode
uv run python vision_agent.py start
```

The agent will:
1. Connect to LiveKit Cloud
2. Wait for rooms to be created (via API `/sessions/start`)
3. Join rooms as a participant
4. Listen for user speech and video
5. Respond with scene descriptions and assistance

## Customization

### Create Your Own Agent

Copy `vision_agent.py` and modify:

**Change the AI models:**
```python
session = AgentSession(
    stt="assemblyai/universal-streaming",  # Different STT
    llm=openai.LLM(model="gpt-4o"),        # Different LLM
    tts="cartesia/sonic-3",                 # Different TTS
    vad=silero.VAD.load(),
)
```

**Customize instructions:**
```python
class CustomAssistant(Agent):
    def __init__(self) -> None:
        super().__init__(
            instructions="""Your custom system prompt here.
            Describe how the agent should behave."""
        )
```

**Add custom logic:**
```python
async def on_user_turn_completed(self, chat_ctx, new_message):
    # Custom processing before LLM
    if self._latest_frame:
        # Analyze frame, add metadata, etc.
        new_message.content.append(llm.ChatImage(image=self._latest_frame))
```

### Supported Models

**STT (Speech-to-Text):**
- `deepgram/nova-2` - Fast, accurate
- `assemblyai/universal-streaming` - Multilingual
- See [LiveKit STT docs](https://docs.livekit.io/agents/models/stt/)

**LLM (Language Models):**
- `google/gemini-2.0-flash-exp:free` - Vision support via OpenRouter
- `openai/gpt-4o` - OpenAI multimodal
- `anthropic/claude-sonnet-4.5` - Anthropic via OpenRouter
- See [LiveKit LLM docs](https://docs.livekit.io/agents/models/llm/)

**TTS (Text-to-Speech):**
- `elevenlabs` - Natural, expressive voices
- `cartesia/sonic-3` - Fast, low latency
- `openai/tts-1` - OpenAI voices
- See [LiveKit TTS docs](https://docs.livekit.io/agents/models/tts/)

## Agent Prefix System

When starting a session via the API, you can specify an `agent_id`:

```bash
curl -X POST http://localhost:8000/sessions/start \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "agent_id": "vision-v2"
  }'
```

Then run your agent worker with a filter:

```python
# In your custom agent
@server.rtc_session()
async def my_agent(ctx: JobContext) -> None:
    # Only handle rooms with matching agent_id
    # (requires custom room metadata filtering)
    session = AgentSession(...)
    await session.start(room=ctx.room, agent=MyAssistant())
```

## Replay Functionality

The `segments` table in the database tracks conversation turns for replay:

**Capture segments** - Log each turn with timestamps and metadata
**Replay sessions** - Process stored segments with a different AI agent

This allows experimenting with different models on the same conversation.

## Deployment

### Development
```bash
uv run python vision_agent.py dev
```

### Production
```bash
# Run as a service
uv run python vision_agent.py start

# Or with systemd, Docker, etc.
```

### Multiple Agents

You can run multiple agent workers simultaneously:

```bash
# Terminal 1 - Vision agent
uv run python vision_agent.py dev

# Terminal 2 - Custom agent
uv run python custom_agent.py dev
```

Each agent worker can handle multiple rooms concurrently.

## Troubleshooting

**Agent not joining rooms:**
- Check LiveKit credentials in `.env`
- Verify agent can connect: `uv run python vision_agent.py dev`
- Check LiveKit Cloud dashboard for connected agents

**No video frames:**
- Ensure user grants camera permission in iOS app
- Check video track is published: LiveKit dashboard > Room > Tracks
- Verify agent subscribed: Check logs for "Subscribed to existing video track"

**TTS not working:**
- Verify ElevenLabs API key in `.env`
- Check API quota/limits
- Try different TTS provider (Cartesia, OpenAI)

**LLM errors:**
- Verify OpenRouter API key for Gemini
- Check model name is correct
- Try different model (GPT-4, Claude)

## Resources

- [LiveKit Agents Docs](https://docs.livekit.io/agents/)
- [LiveKit Python SDK](https://github.com/livekit/python-sdks)
- [Vision Agent Example](https://docs.livekit.io/agents/build/vision)
