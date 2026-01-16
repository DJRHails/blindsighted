# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Blindsighted is a mobile app with FastAPI backend that provides AI-powered visual assistance for blind/visually impaired users using Meta AI Glasses (Ray-Ban Meta).

**Architecture**: Monorepo with two main components:

- `ios/` - Native iOS app (Swift/SwiftUI) using Meta Wearables DAT SDK for Ray-Ban Meta glasses
- `api/` - FastAPI backend (Python 3.11) that processes frames using Gemini vision and ElevenLabs TTS

**Flow**: Glasses capture photo → App sends base64 image to API → Gemini describes scene → ElevenLabs converts to speech → Audio played to user

## Development Commands

### iOS App (Swift/SwiftUI)

```bash
cd ios
open Blindsighted.xcodeproj     # Open in Xcode

# Build and run on simulator
xcodebuild -project Blindsighted.xcodeproj \
  -scheme Blindsighted \
  -sdk iphonesimulator \
  -destination 'platform=iOS Simulator,name=iPhone 15 Pro'

# Build for device
xcodebuild -project Blindsighted.xcodeproj \
  -scheme Blindsighted \
  -sdk iphoneos
```

**Dependencies**:

- Meta Wearables DAT SDK (integrated via Swift Package Manager in Xcode)
  - `MWDATCore` - Core wearables functionality
  - `MWDATCamera` - Camera streaming and photo capture
  - Package URL: `https://github.com/facebook/meta-wearables-dat-ios`
  - Version: 0.3.0

**Note**: The app is based on Meta's CameraAccess sample from the DAT SDK, customized for Blindsighted.

**Adding New Files to Xcode Project**:

When creating new Swift files outside of Xcode, you must add them to the project file using the xcodeproj gem.

**One-time setup:**

```bash
gem install xcodeproj --user-install
```

**To add a file:**

```bash
cd ios
ruby -e "
require 'xcodeproj'
project = Xcodeproj::Project.open('Blindsighted.xcodeproj')
target = project.targets.first
group = project.main_group.find_subpath('GROUP_PATH', false)
file_ref = group.new_reference('FILENAME.swift')
target.add_file_references([file_ref])
project.save
"
```

**Common group paths:**
| Group Path | Purpose | Example Files |
|------------|---------|---------------|
| `Blindsighted/Utils` | Utility classes | VideoRecorder.swift, AudioManager.swift, LocationManager.swift |
| `Blindsighted/ViewModels` | View models | StreamSessionViewModel.swift |
| `Blindsighted/Views` | SwiftUI views | StreamView.swift, VideoGalleryView.swift, AudioTestView.swift |
| `Blindsighted/Views/Components` | Reusable UI components | CircleButton.swift, CustomButton.swift |

**Examples:**

```bash
# Add LocationManager.swift to Utils group
cd ios
ruby -e "
require 'xcodeproj'
project = Xcodeproj::Project.open('Blindsighted.xcodeproj')
target = project.targets.first
group = project.main_group.find_subpath('Blindsighted/Utils', false)
file_ref = group.new_reference('LocationManager.swift')
target.add_file_references([file_ref])
project.save
"
```

**Important**: Always add new files to the Xcode project, or the build will fail with "file not found" errors.

**iOS Configuration**:

The iOS app uses Xcode configuration files (`.xcconfig`) for environment-specific settings like LiveKit credentials. This is similar to `.env` files but native to Xcode.

**Setup**:

1. Copy `ios/Config.xcconfig.example` to `ios/Config.xcconfig`:
   ```bash
   cd ios
   cp Config.xcconfig.example Config.xcconfig
   ```

2. Edit `Config.xcconfig` with your credentials:
   ```bash
   # API Backend Configuration
   API_BASE_URL = http:/$()/localhost:8000

   # LiveKit Server Configuration
   LIVEKIT_SERVER_URL = wss:/$()/your-livekit-server.com
   LIVEKIT_API_KEY = your_api_key_here
   LIVEKIT_API_SECRET = your_api_secret_here

   # Development Configuration (for hardcoded token testing)
   # For production, leave these empty to use API mode
   LIVEKIT_DEV_TOKEN = eyJhbGc...your-dev-token
   LIVEKIT_DEV_ROOM_NAME = test-room
   ```

3. Link the xcconfig file to your Xcode project:
   - Open `Blindsighted.xcodeproj` in Xcode
   - Select the project in Project Navigator
   - Under "Info" tab → "Configurations" section
   - For both Debug and Release, select `Config` for the Blindsighted target

**Notes**:
- `Config.xcconfig` is gitignored and should never be committed
- The app reads these values from `Info.plist` at runtime via `LiveKitConfig.loadFromInfoPlist()`
- **Development mode**: If `LIVEKIT_DEV_TOKEN` is set, the app uses manual mode with the hardcoded token (no API calls needed)
- **Production mode**: If `LIVEKIT_DEV_TOKEN` is empty/unset, the app uses API mode and calls `/sessions/start` to get tokens dynamically
- The app automatically switches between dev and prod modes based on whether a dev token is configured

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
- **iOS App**: Configuration is managed via Info.plist and app entitlements. No external config files needed for the iOS app itself.

## CI/CD & Releases

### iOS Build

iOS builds are performed using Xcode and can be distributed via:

- **Development**: Build directly from Xcode to physical device or simulator
- **TestFlight**: Archive and upload to App Store Connect for beta testing
- **App Store**: Production releases via App Store Connect

**Creating an Archive**:

1. In Xcode: Product → Archive
2. Window → Organizer to manage archives
3. Distribute App → choose distribution method

### GitHub Actions Workflows

- **PR Checks** (`.github/workflows/pr-checks.yml`): Lint/format (ruff), type check (mypy) for API
- **Release** (`.github/workflows/release.yml`): Triggered on `v*.*.*` tags
  - Builds Docker image for API and pushes to `ghcr.io/djrhails/blindsighted/api`
  - Creates GitHub release with changelog

**Creating a Release**:

```bash
git tag v1.2.3
git push origin v1.2.3
```

### Package Manager

- **iOS App**: Swift Package Manager (integrated in Xcode)
- **API**: Uses `uv` for Python dependency management

## Python Code Style

- **Line length**: 100 characters (ruff config)
- **Type hints**: Strict mode enabled, all functions must have type hints
- **Imports**: Auto-sorted by ruff (isort)
- **Python version**: 3.11+ required

## Swift Code Style

- **Idiomatic Swift**: Prefer modern SwiftUI patterns over UIKit
- **UI Components**: Use SwiftUI views exclusively (no `UIViewControllerRepresentable` for UI)
  - Use `ShareLink` instead of `UIActivityViewController`
  - Use `PhotosPicker` instead of `UIImagePickerController`
  - Avoid UIKit UI components in views
- **Data Models**: UIKit types like `UIImage` are acceptable as data models
- **Low-level APIs**: Core Graphics, AVFoundation, etc. are fine when no SwiftUI alternative exists
- **SwiftUI Best Practices**: Use `@StateObject`, `@ObservedObject`, declarative views

## iOS App Architecture

- **UI Framework**: SwiftUI with declarative views
- **State Management**: SwiftUI's `@StateObject`, `@ObservedObject`, and `@Published` properties
- **Architecture Pattern**: MVVM (Model-View-ViewModel)
  - **Views**: SwiftUI views in `ios/Blindsighted/Views/`
  - **ViewModels**: Observable objects in `ios/Blindsighted/ViewModels/`
  - **Models**: Data models from Meta Wearables DAT SDK

### Key Components

- **WearablesViewModel** (`ios/Blindsighted/ViewModels/WearablesViewModel.swift`): Manages device connection and registration
- **StreamSessionViewModel** (`ios/Blindsighted/ViewModels/StreamSessionViewModel.swift`): Handles video streaming, photo capture, and session state
- **Meta Wearables DAT SDK Integration**:
  - SDK configured once at app launch in `BlindsightedApp.swift`
  - Listener pattern for SDK events (state changes, video frames, errors)
  - `StreamSession` manages streaming lifecycle

### Video Streaming Flow

1. User taps "Start Streaming" → requests camera permission
2. `StreamSession.start()` initiates connection to glasses
3. Video frames received via `videoFramePublisher` listener
4. Frames converted to `UIImage` and displayed in real-time
5. User can capture photos during stream with `capturePhoto()`

### Utility Managers

- **AudioManager** (`ios/Blindsighted/Utils/AudioManager.swift`): Manages audio routing to Meta Wearables
  - Configures `AVAudioSession` for Bluetooth audio with `.allowBluetoothHFP` and `.allowBluetoothA2DP`
  - Provides stereo panning control for left/right ear audio testing
  - Generates sine wave ping sounds for audio channel verification
  - Monitors audio route changes (device connect/disconnect)
- **AudioTestView** (`ios/Blindsighted/Views/AudioTestView.swift`): UI for testing audio routing to glasses
  - Test left, right, or center (both) audio channels
  - Display current audio route and session configuration
  - Auto-configures audio session on appear
- **LocationManager** (`ios/Blindsighted/Utils/LocationManager.swift`): Manages location services for video metadata
  - Captures GPS coordinates and heading during video recording
  - Requests "when in use" location permission
  - Updates every 10 meters with `kCLLocationAccuracyBest`
  - Provides `currentLocation` and `currentHeading` as published properties

### Dark Mode Support

The app fully supports both light and dark mode appearances. When working with UI:

**Best Practices**:
- **NEVER use hardcoded backgrounds**: Avoid `.background(Color.white)` or `.background(Color.black)` on views
- **Use semantic colors**: Prefer `.foregroundColor(.secondary)` over `.foregroundColor(.gray)`
- **System-adaptive colors**: SwiftUI's semantic colors automatically adapt to appearance:
  - `.primary` - Primary label color (black in light, white in dark)
  - `.secondary` - Secondary label color (automatically adjusts)
  - `.tertiary` - Tertiary label color
- **Transparent overlays**: Use opacity for backgrounds: `Color.gray.opacity(0.1)` works in both modes
- **Testing**: Always test UI in both light and dark mode to ensure readability

**Examples**:

```swift
// ✅ Good - Adapts to dark/light mode
VStack {
  Text("Title")
    .foregroundColor(.primary)
  Text("Subtitle")
    .foregroundColor(.secondary)
}
.background(Color.gray.opacity(0.1))

// ❌ Bad - Hardcoded colors, breaks in dark mode
VStack {
  Text("Title")
    .foregroundColor(.black)
  Text("Subtitle")
    .foregroundColor(.gray)
}
.background(Color.white)
```

## Troubleshooting

### iOS Build Requirements

- **Xcode**: 26.2+
- **Swift**: 6.2+
- **iOS Deployment Target**: 17.0+

The project is configured for:

- Swift version: 6.2 (in `ios/Blindsighted.xcodeproj/project.pbxproj`)
- iOS deployment target: 17.0 (matches Meta Wearables SDK requirement)

### Meta Wearables SDK Package Not Found

If you see errors like `Missing package product 'MWDATCore'` or `Missing package product 'MWDATCamera'`:

**Problem**: Swift Package Manager may not automatically resolve packages.

**Solution 1: Resolve in Xcode** (Recommended)

1. Open `ios/Blindsighted.xcodeproj` in Xcode
2. Go to **File → Packages → Resolve Package Versions**
3. Wait for resolution to complete
4. Clean build folder: **Product → Clean Build Folder** (⇧⌘K)
5. Build the project

**Solution 2: Manually Add SPM Dependency**
If automatic resolution fails, manually add the package:

1. Open `ios/Blindsighted.xcodeproj` in Xcode
2. Select the **Blindsighted** project in Project Navigator
3. Select the **Blindsighted** target
4. Go to **General** tab → **Frameworks, Libraries, and Embedded Content**
5. Click **+** → **Add Package Dependency**
6. Enter: `https://github.com/facebook/meta-wearables-dat-ios`
7. Set version: **Exact Version 0.3.0**
8. Select products: **MWDATCore** and **MWDATCamera**
9. Clean and rebuild

**Solution 3: Clear Derived Data**

```bash
rm -rf ~/Library/Developer/Xcode/DerivedData/Blindsighted-*
```

Then open Xcode and use Solution 1 or 2.

### Swift Version Mismatch

If you see Swift version errors:

1. Open `ios/Blindsighted.xcodeproj` in Xcode
2. Select the **Blindsighted** project in Project Navigator
3. Select the **Blindsighted** target
4. Go to **Build Settings** tab
5. Search for "Swift Language Version"
6. Ensure it's set to **Swift 6.2** (or 6.0+)
7. Clean build folder: **Product → Clean Build Folder** (⇧⌘K)
8. Rebuild the project
