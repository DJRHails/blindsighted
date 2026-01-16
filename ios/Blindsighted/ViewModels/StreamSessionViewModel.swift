//
// StreamSessionViewModel.swift
//
// Core view model demonstrating video streaming from Meta wearable devices using the DAT SDK.
// This class showcases the key streaming patterns: device selection, session management,
// video frame handling, photo capture, and error handling.
//

import MWDATCamera
import MWDATCore
import SwiftUI
import CoreMedia

enum StreamingStatus {
  case streaming
  case waiting
  case stopped
}

@MainActor
class StreamSessionViewModel: ObservableObject {
  @Published var currentVideoFrame: UIImage?
  @Published var hasReceivedFirstFrame: Bool = false
  @Published var streamingStatus: StreamingStatus = .stopped
  @Published var showError: Bool = false
  @Published var errorMessage: String = ""
  @Published var hasActiveDevice: Bool = false

  var isStreaming: Bool {
    streamingStatus != .stopped
  }

  // Photo capture properties
  @Published var capturedPhoto: UIImage?
  @Published var showPhotoPreview: Bool = false

  // Video recording properties
  @Published var isRecording: Bool = false
  @Published var recordingDuration: TimeInterval = 0
  private var videoRecorder: VideoRecorder?
  private var recordingURL: URL?
  private var detectedVideoSize: CGSize?
  private var recordingMetadata: VideoMetadata?
  private let locationManager = LocationManager.shared

  // LiveKit streaming properties
  @Published var isLiveKitConnected: Bool = false
  private var liveKitManager: LiveKitManager?
  private var liveKitConfig: LiveKitConfig?
  private var liveKitSessionId: Int?  // Track session ID for cleanup
  private var apiClient: APIClient?
  private var frameCount: Int64 = 0

  // The core DAT SDK StreamSession - handles all streaming operations
  private var streamSession: StreamSession
  // Listener tokens are used to manage DAT SDK event subscriptions
  private var stateListenerToken: AnyListenerToken?
  private var videoFrameListenerToken: AnyListenerToken?
  private var errorListenerToken: AnyListenerToken?
  private var photoDataListenerToken: AnyListenerToken?
  private let wearables: WearablesInterface
  private let deviceSelector: AutoDeviceSelector
  private var deviceMonitorTask: Task<Void, Never>?

  init(wearables: WearablesInterface) {
    self.wearables = wearables
    // Let the SDK auto-select from available devices
    self.deviceSelector = AutoDeviceSelector(wearables: wearables)
    let config = StreamSessionConfig(
      videoCodec: VideoCodec.raw,
      resolution: StreamingResolution.high,
      frameRate: 24)
    streamSession = StreamSession(streamSessionConfig: config, deviceSelector: deviceSelector)

    // Load LiveKit configuration if available
    if let liveKitConfig = LiveKitConfig.loadFromUserDefaults() {
      self.liveKitConfig = liveKitConfig
      self.liveKitManager = LiveKitManager()
    }

    // Monitor device availability
    deviceMonitorTask = Task { @MainActor in
      for await device in deviceSelector.activeDeviceStream() {
        self.hasActiveDevice = device != nil
      }
    }

    // Request location permissions and start location updates
    locationManager.requestPermission()
    if locationManager.authorizationStatus == .authorizedWhenInUse ||
       locationManager.authorizationStatus == .authorizedAlways {
      locationManager.startUpdatingLocation()
    }

    // Subscribe to session state changes using the DAT SDK listener pattern
    // State changes tell us when streaming starts, stops, or encounters issues
    stateListenerToken = streamSession.statePublisher.listen { [weak self] state in
      Task { @MainActor [weak self] in
        self?.updateStatusFromState(state)
      }
    }

    // Subscribe to video frames from the device camera
    // Each VideoFrame contains the raw camera data that we convert to UIImage
    videoFrameListenerToken = streamSession.videoFramePublisher.listen { [weak self] videoFrame in
      Task { @MainActor [weak self] in
        guard let self else { return }

        if let image = videoFrame.makeUIImage() {
          self.currentVideoFrame = image
          let wasFirstFrame = !self.hasReceivedFirstFrame
          if !self.hasReceivedFirstFrame {
            self.hasReceivedFirstFrame = true
          }
          // Detect video size from first frame
          if self.detectedVideoSize == nil {
            self.detectedVideoSize = image.size
            NSLog("[Blindsighted] Detected video size: \(image.size.width)x\(image.size.height)")
            // Start recording now that we know the correct video dimensions
            if wasFirstFrame && self.streamingStatus == .streaming && !self.isRecording {
              self.startRecording()
            }
            // Start LiveKit publishing if connected
            if wasFirstFrame && self.isLiveKitConnected {
              self.startLiveKitPublishing()
            }
          }
        }

        // Publish frame to LiveKit if connected
        if self.isLiveKitConnected, let manager = self.liveKitManager, manager.isPublishingVideo {
          if let pixelBuffer = videoFrame.makePixelBuffer(targetSize: self.detectedVideoSize ?? CGSize(width: 1280, height: 720)) {
            // Calculate timestamp for this frame
            let timestamp = CMTime(value: CMTimeValue(self.frameCount), timescale: 24)
            manager.publishVideoFrame(pixelBuffer, timestamp: timestamp)
          }
        }

        // Record frame if recording is active
        if self.isRecording, let recorder = self.videoRecorder {
          do {
            try recorder.appendFrame(videoFrame)
            self.recordingDuration = recorder.recordingDuration
          } catch {
            NSLog("[Blindsighted] Failed to append video frame: \(error)")
          }
        }

        self.frameCount += 1
      }
    }

    // Subscribe to streaming errors
    // Errors include device disconnection, streaming failures, etc.
    errorListenerToken = streamSession.errorPublisher.listen { [weak self] error in
      Task { @MainActor [weak self] in
        guard let self else { return }
        let newErrorMessage = formatStreamingError(error)
        if newErrorMessage != self.errorMessage {
          showError(newErrorMessage)
        }
      }
    }

    updateStatusFromState(streamSession.state)

    // Subscribe to photo capture events
    // PhotoData contains the captured image in the requested format (JPEG/HEIC)
    photoDataListenerToken = streamSession.photoDataPublisher.listen { [weak self] photoData in
      Task { @MainActor [weak self] in
        guard let self else { return }
        if let uiImage = UIImage(data: photoData.data) {
          self.capturedPhoto = uiImage
          self.showPhotoPreview = true
        }
      }
    }
  }

  func handleStartStreaming() async {
    let permission = Permission.camera
    do {
      let status = try await wearables.checkPermissionStatus(permission)
      if status == .granted {
        await startSession()
        return
      }
      let requestStatus = try await wearables.requestPermission(permission)
      if requestStatus == .granted {
        await startSession()
        return
      }
      showError("Permission denied")
    } catch {
      showError("Permission error: \(error.description)")
    }
  }

  func startSession() async {
    await streamSession.start()

    // Auto-connect to LiveKit if configured
    if let config = liveKitConfig, let manager = liveKitManager, !isLiveKitConnected {
      do {
        // Get credentials based on mode
        let credentials: LiveKitSessionCredentials
        switch config.mode {
        case .api:
          // Fetch token from API
          guard let apiURL = config.apiURL else {
            throw LiveKitError.invalidConfiguration
          }
          let client = APIClient(baseURL: apiURL)
          self.apiClient = client

          // Generate unique device ID for this device
          let deviceId = "glasses-\(UIDevice.current.identifierForVendor?.uuidString.prefix(8) ?? "unknown")"
          let response = try await client.startSession(deviceId: deviceId)

          credentials = LiveKitSessionCredentials(
            sessionId: response.sessionId,
            serverURL: response.livekitUrl,
            token: response.token,
            roomName: response.roomName
          )
          self.liveKitSessionId = response.sessionId
          NSLog("[Blindsighted] LiveKit session started via API: \(response.roomName)")

        case .manual:
          // Use manual credentials
          guard let serverURL = config.serverURL,
                let token = config.token,
                let roomName = config.roomName else {
            throw LiveKitError.invalidConfiguration
          }
          credentials = LiveKitSessionCredentials(
            sessionId: nil,
            serverURL: serverURL,
            token: token,
            roomName: roomName
          )
          NSLog("[Blindsighted] Using manual LiveKit credentials")
        }

        // Connect to LiveKit with credentials
        try await manager.connect(credentials: credentials, config: config)
        isLiveKitConnected = true
      } catch {
        showError("LiveKit connection failed: \(error.localizedDescription)")
      }
    }
  }

  private func showError(_ message: String) {
    errorMessage = message
    showError = true
  }

  func stopSession() async {
    if isRecording {
      await stopRecording()
    }

    // Disconnect from LiveKit
    if isLiveKitConnected, let manager = liveKitManager {
      await manager.disconnect()
      isLiveKitConnected = false

      // Stop session via API if using API mode
      if let config = liveKitConfig, config.mode == .api,
         let sessionId = liveKitSessionId,
         let client = apiClient {
        do {
          _ = try await client.stopSession(sessionId: sessionId)
          NSLog("[Blindsighted] LiveKit session stopped via API")
        } catch {
          NSLog("[Blindsighted] Failed to stop API session: \(error.localizedDescription)")
        }
        self.liveKitSessionId = nil
        self.apiClient = nil
      }
    }

    await streamSession.stop()
  }

  func dismissError() {
    showError = false
    errorMessage = ""
  }

  func capturePhoto() {
    streamSession.capturePhoto(format: .jpeg)
  }

  func dismissPhotoPreview() {
    showPhotoPreview = false
    capturedPhoto = nil
  }

  func startRecording() {
    guard isStreaming && !isRecording else { return }

    // Must have detected video size from first frame
    guard let videoSize = detectedVideoSize else {
      NSLog("[Blindsighted] Cannot start recording: video size not yet detected")
      return
    }

    // Capture location metadata at start of recording
    let metadata = VideoMetadata(
      location: locationManager.currentLocation,
      heading: locationManager.currentHeading
    )
    self.recordingMetadata = metadata

    do {
      let url = VideoFileManager.shared.generateVideoURL()
      let recorder = VideoRecorder(outputURL: url, videoSize: videoSize, frameRate: 24)
      try recorder.startRecording()

      self.videoRecorder = recorder
      self.recordingURL = url
      self.isRecording = true
      self.recordingDuration = 0

      NSLog("[Blindsighted] Started recording to: \(url.path) at \(videoSize.width)x\(videoSize.height)")
      if let lat = metadata.latitude, let lon = metadata.longitude {
        NSLog("[Blindsighted] Location: \(lat), \(lon)")
      }
    } catch {
      showError("Failed to start recording: \(error.localizedDescription)")
    }
  }

  func stopRecording() async {
    guard isRecording, let recorder = videoRecorder else { return }

    isRecording = false

    do {
      let savedURL = try await recorder.stopRecording()
      NSLog("[Blindsighted] Video saved to: \(savedURL.path)")

      // Save metadata alongside video
      if let metadata = recordingMetadata {
        let filename = savedURL.lastPathComponent
        try? VideoFileManager.shared.saveMetadata(metadata, for: filename)
        NSLog("[Blindsighted] Metadata saved for: \(filename)")
      }

      // Show success message
      showError = false
      errorMessage = "Video saved successfully"
    } catch {
      showError("Failed to save recording: \(error.localizedDescription)")
    }

    videoRecorder = nil
    recordingURL = nil
    recordingDuration = 0
    recordingMetadata = nil
  }

  // MARK: - LiveKit Methods

  /// Start publishing video and audio to LiveKit after first frame
  private func startLiveKitPublishing() {
    guard isLiveKitConnected, let manager = liveKitManager, let videoSize = detectedVideoSize else {
      return
    }

    Task {
      do {
        // Start publishing video
        try await manager.startPublishingVideo(videoSize: videoSize, frameRate: 24)
        NSLog("[Blindsighted] Started LiveKit video publishing at \(videoSize.width)x\(videoSize.height)")

        // Start publishing audio
        try await manager.startPublishingAudio()
        NSLog("[Blindsighted] Started LiveKit audio publishing")
      } catch {
        showError("Failed to start LiveKit publishing: \(error.localizedDescription)")
      }
    }
  }

  /// Manually connect to LiveKit (can be called from UI)
  func connectToLiveKit() async throws {
    guard let config = liveKitConfig else {
      throw LiveKitError.notConfigured
    }

    let manager = liveKitManager ?? LiveKitManager()
    self.liveKitManager = manager

    // Get credentials based on mode
    let credentials: LiveKitSessionCredentials
    switch config.mode {
    case .api:
      guard let apiURL = config.apiURL else {
        throw LiveKitError.invalidConfiguration
      }
      let client = APIClient(baseURL: apiURL)
      self.apiClient = client

      let deviceId = "glasses-\(UIDevice.current.identifierForVendor?.uuidString.prefix(8) ?? "unknown")"
      let response = try await client.startSession(deviceId: deviceId)

      credentials = LiveKitSessionCredentials(
        sessionId: response.sessionId,
        serverURL: response.livekitUrl,
        token: response.token,
        roomName: response.roomName
      )
      self.liveKitSessionId = response.sessionId

    case .manual:
      guard let serverURL = config.serverURL,
            let token = config.token,
            let roomName = config.roomName else {
        throw LiveKitError.invalidConfiguration
      }
      credentials = LiveKitSessionCredentials(
        sessionId: nil,
        serverURL: serverURL,
        token: token,
        roomName: roomName
      )
    }

    try await manager.connect(credentials: credentials, config: config)
    isLiveKitConnected = true
  }

  /// Manually disconnect from LiveKit (can be called from UI)
  func disconnectFromLiveKit() async {
    guard let manager = liveKitManager else { return }

    await manager.disconnect()
    isLiveKitConnected = false

    // Stop session via API if using API mode
    if let config = liveKitConfig, config.mode == .api,
       let sessionId = liveKitSessionId,
       let client = apiClient {
      do {
        _ = try await client.stopSession(sessionId: sessionId)
      } catch {
        NSLog("[Blindsighted] Failed to stop API session: \(error.localizedDescription)")
      }
      self.liveKitSessionId = nil
      self.apiClient = nil
    }
  }

  /// Update LiveKit configuration
  func updateLiveKitConfig(_ config: LiveKitConfig) {
    self.liveKitConfig = config
    if liveKitManager == nil {
      liveKitManager = LiveKitManager()
    }
  }

  private func updateStatusFromState(_ state: StreamSessionState) {
    switch state {
    case .stopped:
      currentVideoFrame = nil
      streamingStatus = .stopped
      detectedVideoSize = nil  // Reset for next stream
      frameCount = 0  // Reset frame counter
    case .waitingForDevice, .starting, .stopping, .paused:
      streamingStatus = .waiting
    case .streaming:
      streamingStatus = .streaming
      frameCount = 0  // Reset frame counter at start of streaming
      // Recording will start automatically after first frame arrives and video size is detected
    }
  }

  private func formatStreamingError(_ error: StreamSessionError) -> String {
    switch error {
    case .internalError:
      return "An internal error occurred. Please try again."
    case .deviceNotFound:
      return "Device not found. Please ensure your device is connected."
    case .deviceNotConnected:
      return "Device not connected. Please check your connection and try again."
    case .timeout:
      return "The operation timed out. Please try again."
    case .videoStreamingError:
      return "Video streaming failed. Please try again."
    case .audioStreamingError:
      return "Audio streaming failed. Please try again."
    case .permissionDenied:
      return "Camera permission denied. Please grant permission in Settings."
    @unknown default:
      return "An unknown streaming error occurred."
    }
  }
}
