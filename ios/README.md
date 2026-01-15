# Blindsighted iOS App

A native iOS application providing AI-powered visual assistance for blind/visually impaired users using Ray-Ban Meta smart glasses. This app uses the Meta Wearables Device Access Toolkit to stream live video, record sessions, and capture photos from the glasses.

## Attribution

This app is based on the [CameraAccess sample](https://github.com/facebook/meta-wearables-dat-ios/tree/main/samples/CameraAccess) from Meta's [meta-wearables-dat-ios](https://github.com/facebook/meta-wearables-dat-ios) repository. The sample code has been customized and extended for the Blindsighted project.

## Features

- **Live Video Streaming**: Real-time camera feed from Ray-Ban Meta glasses
- **Video Recording**: Record and save video sessions to device storage
- **Photo Capture**: Capture still photos from the video stream
- **Video Gallery**: Browse, playback, and manage recorded videos with thumbnails
- **Timer-based Sessions**: Set automatic stream duration limits
- **Share & Export**: Share photos and videos via iOS share sheet

## Prerequisites

- iOS 17.0+
- Xcode 14.0+
- Swift 5.0+
- Meta Wearables Device Access Toolkit (included as a dependency)
- A Meta AI glasses device for testing (optional for development)

## Building the app

### Using Xcode

1. Clone this repository
1. Open the project in Xcode
1. Select your target device
1. Click the "Build" button or press `Cmd+B` to build the project
1. To run the app, click the "Run" button (▶️) or press `Cmd+R`

## Running the app

1. Turn 'Developer Mode' on in the Meta AI app.
1. Launch the app.
1. Press the "Connect" button to complete app registration.
1. Once connected, the camera stream from the device will be displayed

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
