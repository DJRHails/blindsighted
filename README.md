# Blindsighted

AI-powered visual assistance app for blind/visually impaired users using Ray-Ban Meta smart glasses. Native iOS app with FastAPI backend.

## Project Structure

```
blindsighted/
├── ios/          # Native iOS app (Swift/SwiftUI)
└── api/          # FastAPI backend (Python)
```

## Quick Start

### iOS App Setup

1. Navigate to the ios directory:

```bash
cd ios
```

2. Open the Xcode project:

```bash
open Blindsighted.xcodeproj
```

3. Build and run in Xcode (⌘R)

**Requirements**: Xcode 26.2+, iOS 17.0+, Swift 6.2+

See [ios/README.md](ios/README.md) for detailed setup instructions.

### API Setup

1. Navigate to the api directory:

```bash
cd api
```

2. Install dependencies using uv:

```bash
uv pip install -e ".[dev]"
```

3. Run the API:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000` with documentation at `http://localhost:8000/docs`

## Features

### iOS App

- Live video streaming from Ray-Ban Meta glasses
- Video recording and storage
- Photo capture
- Video gallery with thumbnails and playback
- Share photos and videos

### API (Future Integration)

- AI-powered scene description using vision models
- Text-to-speech audio generation
- Real-time processing of video frames

## Development

See individual README files in `ios/` and `api/` directories for more details.

## License

See LICENSE file in the root directory. The iOS app incorporates sample code from Meta's meta-wearables-dat-ios repository under its license terms.
