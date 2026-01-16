import LiveKit
import AVFoundation
import CoreMedia
import LiveKitWebRTC

/// Connection state for LiveKit room
enum LiveKitConnectionState: Equatable {
    case disconnected
    case connecting
    case connected
    case error(String)
}

/// Errors specific to LiveKit operations
enum LiveKitError: Error, LocalizedError {
    case notConnected
    case notConfigured
    case videoPublishFailed
    case audioPublishFailed
    case invalidConfiguration
    case videoSourceCreationFailed

    var errorDescription: String? {
        switch self {
        case .notConnected:
            return "Not connected to LiveKit room"
        case .notConfigured:
            return "LiveKit configuration not provided"
        case .videoPublishFailed:
            return "Failed to publish video track"
        case .audioPublishFailed:
            return "Failed to publish audio track"
        case .invalidConfiguration:
            return "Invalid LiveKit configuration"
        case .videoSourceCreationFailed:
            return "Failed to create custom video source"
        }
    }
}

/// Manages LiveKit room connection and media publishing
@MainActor
class LiveKitManager: ObservableObject {
    @Published var connectionState: LiveKitConnectionState = .disconnected
    @Published var isPublishingVideo: Bool = false
    @Published var isPublishingAudio: Bool = false

    private var room: Room?
    private var videoTrack: LocalVideoTrack?
    private var audioTrack: LocalAudioTrack?
    private var config: LiveKitConfig?

    // Custom video capturer for glasses frames
    private var bufferCapturer: BufferCapturer?

    // Track management
    private var frameCount: Int64 = 0
    private var lastFrameTime: CMTime = .zero
    private var startTime: CMTime?

    // MARK: - Room Connection

    /// Connect to LiveKit room with credentials
    func connect(credentials: LiveKitSessionCredentials, config: LiveKitConfig) async throws {
        self.config = config
        connectionState = .connecting

        let room = Room()
        self.room = room

        // Setup room event handlers
        setupRoomHandlers(room)

        do {
            // Connect to room
            try await room.connect(
                url: credentials.serverURL,
                token: credentials.token
            )

            connectionState = .connected
            NSLog("[LiveKit] Connected to room: \(credentials.roomName)")
        } catch {
            connectionState = .error("Connection failed: \(error.localizedDescription)")
            throw error
        }
    }

    /// Disconnect from LiveKit room
    func disconnect() async {
        await stopPublishingVideo()
        await stopPublishingAudio()
        await room?.disconnect()
        room = nil
        config = nil
        connectionState = .disconnected
    }

    // MARK: - Video Publishing

    /// Start publishing video from glasses with custom video source
    func startPublishingVideo(videoSize: CGSize, frameRate: Int32 = 24) async throws {
        guard let room = room, connectionState == .connected else {
            throw LiveKitError.notConnected
        }

        guard let config = config, config.enableVideo else {
            return
        }

        do {
            // Create custom video track from buffer for glasses frames
            let track = try LocalVideoTrack.createBufferTrack(
                name: "glasses-video",
                source: .camera,
                options: BufferCaptureOptions(
                    dimensions: Dimensions(
                        width: Int32(videoSize.width),
                        height: Int32(videoSize.height)
                    ),
                    fps: Int(frameRate)
                ),
                reportStatistics: true
            )

            // Get the buffer capturer from the track
            self.bufferCapturer = track.capturer as? BufferCapturer
            self.videoTrack = track
            self.startTime = nil
            self.frameCount = 0

            // Publish the custom video track
            try await room.localParticipant.publish(videoTrack: track)

            isPublishingVideo = true
            NSLog("[LiveKit] Started publishing custom video track at \(videoSize.width)x\(videoSize.height)")
        } catch {
            NSLog("[LiveKit] Failed to publish video: \(error)")
            throw LiveKitError.videoPublishFailed
        }
    }

    /// Publish a video frame from glasses to LiveKit
    func publishVideoFrame(_ pixelBuffer: CVPixelBuffer, timestamp: CMTime) {
        guard isPublishingVideo, let bufferCapturer = bufferCapturer else {
            return
        }

        // Initialize start time on first frame
        if startTime == nil {
            startTime = timestamp
        }

        // Calculate frame timestamp relative to start (in nanoseconds)
        let relativeTime = CMTimeSubtract(timestamp, startTime ?? .zero)
        let timeStampNs = Int64(CMTimeGetSeconds(relativeTime) * 1_000_000_000)

        // Push frame to buffer capturer
        bufferCapturer.capture(
            pixelBuffer,
            timeStampNs: timeStampNs,
            rotation: ._0
        )

        frameCount += 1
    }

    /// Stop publishing video
    func stopPublishingVideo() async {
        guard let room = room, let track = videoTrack else { return }

        do {
            // Find the publication for this track
            if let publication = room.localParticipant.localVideoTracks.first(where: { $0.track === track }) {
                try await room.localParticipant.unpublish(publication: publication)
            }

            videoTrack = nil
            bufferCapturer = nil
            isPublishingVideo = false
            startTime = nil
            frameCount = 0
            NSLog("[LiveKit] Stopped publishing video track")
        } catch {
            NSLog("[LiveKit] Error stopping video publishing: \(error)")
        }
    }

    // MARK: - Audio Publishing

    /// Start publishing audio from glasses microphone
    func startPublishingAudio() async throws {
        guard let room = room, connectionState == .connected else {
            throw LiveKitError.notConnected
        }

        guard let config = config, config.enableAudio else {
            return
        }

        do {
            // Enable microphone track
            try await room.localParticipant.setMicrophone(enabled: true)

            // Get the published microphone track
            if let publication = room.localParticipant.localAudioTracks.first {
                self.audioTrack = publication.track as? LocalAudioTrack
                isPublishingAudio = true
            }
        } catch {
            throw LiveKitError.audioPublishFailed
        }
    }

    /// Publish an audio buffer to LiveKit
    func publishAudioBuffer(_ sampleBuffer: CMSampleBuffer) {
        guard isPublishingAudio else { return }

        // For LiveKit's built-in microphone track, audio is automatically captured
        // Custom audio publishing would require a custom audio source

        // TODO: Implement custom audio source if needed for Bluetooth routing
    }

    /// Stop publishing audio
    func stopPublishingAudio() async {
        guard let room = room else { return }

        do {
            try await room.localParticipant.setMicrophone(enabled: false)
            audioTrack = nil
            isPublishingAudio = false
        } catch {
            print("Error stopping audio publishing: \(error)")
        }
    }

    // MARK: - Room Event Handling

    private func setupRoomHandlers(_ room: Room) {
        // Add room delegate
        room.add(delegate: self)
    }

    // MARK: - Helper Methods

    /// Get room participants count
    var participantCount: Int {
        guard let room = room else { return 0 }
        return room.allParticipants.count
    }

    /// Get current room name
    var currentRoomName: String? {
        return room?.name
    }

    /// Check if connected to room
    var isConnected: Bool {
        return connectionState == .connected && room != nil
    }
}

// MARK: - RoomDelegate

extension LiveKitManager: RoomDelegate {
    nonisolated func room(_ room: Room, didUpdateConnectionState connectionState: ConnectionState, from oldValue: ConnectionState) {
        Task { @MainActor in
            switch connectionState {
            case .disconnected:
                self.connectionState = .disconnected
            case .connected:
                self.connectionState = .connected
            case .connecting, .reconnecting:
                self.connectionState = .connecting
            case .disconnecting:
                self.connectionState = .connecting
            @unknown default:
                break
            }
        }
    }

    nonisolated func room(_ room: Room, didFailToConnectWithError error: LiveKit.LiveKitError?) {
        Task { @MainActor in
            self.connectionState = .error("Connection failed: \(error?.localizedDescription ?? "Unknown error")")
        }
    }

    nonisolated func room(_ room: Room, participant: LocalParticipant, didPublishTrack publication: LocalTrackPublication) {
        Task { @MainActor in
            if publication.kind == .video {
                self.isPublishingVideo = true
            } else if publication.kind == .audio {
                self.isPublishingAudio = true
            }
        }
    }

    nonisolated func room(_ room: Room, participant: LocalParticipant, didUnpublishTrack publication: LocalTrackPublication) {
        Task { @MainActor in
            if publication.kind == .video {
                self.isPublishingVideo = false
            } else if publication.kind == .audio {
                self.isPublishingAudio = false
            }
        }
    }

    nonisolated func room(_ room: Room, participant: RemoteParticipant, didSubscribeTrack publication: RemoteTrackPublication) {
        // Handle remote participant track subscription if needed
    }

    nonisolated func room(_ room: Room, participant: RemoteParticipant, didUnsubscribeTrack publication: RemoteTrackPublication) {
        // Handle remote participant track unsubscription if needed
    }
}
