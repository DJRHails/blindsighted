# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blindsighted is a mobile app with FastAPI backend that provides AI-powered visual assistance for blind/visually impaired users using Meta AI Glasses (Ray-Ban Meta).

**Architecture**: Monorepo with two main components:
- `app/` - Expo React Native app (TypeScript) that interfaces with Meta AI Glasses
- `api/` - FastAPI backend (Python 3.11) that processes frames using Gemini vision and ElevenLabs TTS

**Flow**: Glasses capture photo → App sends base64 image to API → Gemini describes scene → ElevenLabs converts to speech → Audio played to user

## Development Commands

### App (Expo/React Native)

```bash
cd app
yarn install                    # Install dependencies
yarn start                      # Start Expo dev server
yarn ios                        # Run on iOS simulator
yarn android                    # Run on Android emulator
npx tsc --noEmit               # Type check
```

**expo-meta-wearables dependency**:
- **Production/EAS builds**: Uses npm package `expo-meta-wearables@^0.2.2` from package.json
- **Local development**: Uses npm package by default, but can be linked for active development

**When to link**: Only if you're actively developing features in `expo-meta-wearables` alongside this app. Most developers won't need this.

**Setup local link** (for expo-meta-wearables development):
```bash
# 1. Clone expo-meta-wearables as a sibling directory
cd /Users/dh/Projects/github.com/DJRHails
git clone https://github.com/DJRHails/expo-meta-wearables.git

# 2. Register the package for linking
cd expo-meta-wearables
yarn install
yarn link

# 3. Link to the app
cd ../blindsighted/app
yarn link expo-meta-wearables
```

**Unlink and return to npm version**:
```bash
cd app
yarn unlink expo-meta-wearables
yarn install --force
```

**How it works**: When linked, local changes to `expo-meta-wearables` are immediately reflected in the app without republishing. EAS builds always use the npm package, ignoring local symlinks.

### API (FastAPI/Python)

```bash
cd api
uv pip install -e ".[dev]"     # Install with dev dependencies
uv pip install -e .            # Install production only
uvicorn main:app --reload --host 0.0.0.0 --port 8000  # Run dev server
ruff check --fix .             # Lint and auto-fix
ruff format .                  # Format code
mypy .                         # Type check
```

**Configuration**: Copy `api/.env.example` to `api/.env` and add:
- `OPENROUTER_API_KEY` - Get from https://openrouter.ai/
- `ELEVENLABS_API_KEY` - Get from https://elevenlabs.io/

### Docker

```bash
cd api
docker build -t blindsighted-api .
docker run -p 8000:8000 --env-file .env blindsighted-api
```

## Code Architecture

### Dependency Injection Pattern (API)

The FastAPI backend uses dependency injection via `Annotated` types. Do NOT create global client instances.

**Correct**:
```python
from typing import Annotated
from fastapi import Depends

def get_client() -> Client:
    return Client()

@app.post("/endpoint")
async def endpoint(client: Annotated[Client, Depends(get_client)]):
    await client.do_something()
```

**Incorrect** (DON'T DO THIS):
```python
# Do not create global instances
global_client = Client()  # ❌ Wrong
```

See `api/main.py:22-30` for examples.

### Configuration Management

- **API**: Uses `pydantic-settings` to load from `.env` files. See `api/config.py`.
- **App**: Constants in `app/src/config/constants.ts` (API_URL, FPS, etc.)

### Video Streaming Service

The app's video stream service (`app/src/services/videoStream.ts`) is a singleton that:
1. Captures frames from Meta Wearables at configured FPS
2. Converts to base64 and sends to API
3. Receives audio response and plays it back

**Key detail**: The streaming interval is managed in `App.tsx` (not in the service), calling `captureAndSendFrame()` periodically.

## CI/CD & Releases

### EAS Build (Expo Application Services)

Builds are triggered via GitHub Actions. EAS requires authentication.

**Setup**:
```bash
cd app
npm install -g eas-cli
eas login
eas build --platform ios --profile development
eas build --platform android --profile development
```

**Build Profiles** (see `app/eas.json`):
- `development` - Dev client with internal distribution
- `preview` - Internal distribution for testing
- `production` - App Store/Play Store builds with auto-increment

### GitHub Actions Workflows

- **PR Checks** (`.github/workflows/pr-checks.yml`): Type check (tsc), lint/format (ruff), type check (mypy)
- **Release** (`.github/workflows/release.yml`): Triggered on `v*.*.*` tags
  - Builds iOS via EAS
  - Builds Android via EAS
  - Builds Docker image and pushes to `ghcr.io/djrhails/blindsighted/api`
  - Creates GitHub release with changelog
- **Manual Build** (`.github/workflows/manual-build.yml`): Manually trigger builds

**Required Secrets**:
- `EXPO_TOKEN` - EAS authentication token (get via `eas login` → `eas whoami --json`)

**Creating a Release**:
```bash
git tag v1.2.3
git push origin v1.2.3
```

### Package Manager Differences

- **App**: Uses `yarn` (has `yarn.lock`)
- **API**: Uses `uv` for Python dependency management
- **CI**: App CI uses `yarn install --frozen-lockfile` for reproducible builds

## Python Code Style

- **Line length**: 100 characters (ruff config)
- **Type hints**: Strict mode enabled, all functions must have type hints
- **Imports**: Auto-sorted by ruff (isort)
- **Python version**: 3.11+ required

## App Architecture Notes

- **State management**: React hooks (useState, useEffect), no Redux
- **Debouncing**: Custom `useDebounce` hook in `app/src/hooks/useDebounce.ts` for UI updates
- **Modal pattern**: Mock Device Kit info shown in Modal component (`App.tsx:239-257`)
- **Meta Wearables SDK**: Initialized once on mount, listeners added for connection/recording events
