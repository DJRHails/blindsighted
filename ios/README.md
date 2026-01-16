# Blindsighted iOS App

**Part of the Blindsighted hackathon template** - a starting point for building AI-powered experiences with Ray-Ban Meta smart glasses.

This iOS app handles the integration with Meta's wearables SDK and LiveKit streaming. It was originally built for visual assistance, but the architecture works for any AI-powered glasses application. Use it as-is, customize it, or use it as a reference for your own implementation.

## What This Component Does

- Connects to Ray-Ban Meta smart glasses via Bluetooth
- Streams video/audio from glasses to LiveKit Cloud (WebRTC)
- Receives audio responses from AI agents and routes to glasses speakers
- Calls FastAPI backend to create sessions and get LiveKit tokens (optional - can use dev mode)
- Records and manages video/photo gallery locally

**See [../ARCHITECTURE.md](../ARCHITECTURE.md) for how this fits into the overall system.**

## Attribution

Based on the [CameraAccess sample](https://github.com/facebook/meta-wearables-dat-ios/tree/main/samples/CameraAccess) from Meta's [meta-wearables-dat-ios](https://github.com/facebook/meta-wearables-dat-ios) repository. Significantly extended with LiveKit integration, audio routing, and session management.

## Features

- **Live Video Streaming**: Real-time camera feed from Ray-Ban Meta glasses
- **Video Recording**: Record and save video sessions to device storage
- **Photo Capture**: Capture still photos from the video stream
- **Video Gallery**: Browse, playback, and manage recorded videos with thumbnails
- **Timer-based Sessions**: Set automatic stream duration limits
- **Share & Export**: Share photos and videos via iOS share sheet

## Prerequisites

- Xcode 26.2+ **IMPORTANT**
- Swift 6.2+ **IMPORTANT**
- An apple developer account
- Xcode 26.2+ **IMPORTANT**
- Swift 6.2+ **IMPORTANT**
- iOS 17.0+
- Meta Wearables Device Access Toolkit (included as a dependency)
- A Meta AI glasses device for testing (optional for development)

## Building the app

### Using Xcode

1. Clone this repository
1. Open the project in Xcode
1. Select your target device (needs to be a real device, not simulator + remember to turn on developer mode!)
1. Add your team in Signing & Capabilities (you need an apple developer account)
1. Click the "Build" button or press `Cmd+B` to build the project
1. To run the app, click the "Run" button (▶️) or press `Cmd+R`

## Running the app

1. Turn 'Developer Mode' on in the Meta AI app.
1. Launch the app.
1. Press the "Connect" button to complete app registration.
1. Once connected, the camera stream from the device will be displayed

## I've updated the iOS code in my IDE, how do I make sure XCode is running the latest?

1. If you've edited a pre-existing file, just run again in XCode
2. If you've added new files, tell Claude to add those files in XCode - instructions for Claude covered in Claude.md

### Stream Tab Controls

- **Record Button** (circle icon): Start/stop video recording
- **Timer Button**: Set automatic stream duration limits
- **Camera Button**: Capture still photos
- **Stop Streaming**: End the streaming session

### Gallery Tab

- Browse all recorded videos with thumbnails
- Tap a video to play it full-screen
- Long-press or swipe left to delete videos
- Share videos via the share button in the player

## Video Storage

Recorded videos are saved to the app's Documents directory under `RecordedVideos/` and persist until manually deleted. Videos are stored in MP4 format with H.264 encoding.

## Troubleshooting

For issues related to the Meta Wearables Device Access Toolkit, please refer to the [developer documentation](https://wearables.developer.meta.com/docs/develop/) or visit our [discussions forum](https://github.com/facebook/meta-wearables-dat-ios/discussions)

## License

This source code is licensed under the license found in the LICENSE file in the root directory of this source tree.
