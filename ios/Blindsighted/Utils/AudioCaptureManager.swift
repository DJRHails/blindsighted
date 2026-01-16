import AVFoundation
import CoreMedia

/// Manages audio capture from Bluetooth microphone (Ray-Ban Meta glasses)
@MainActor
class AudioCaptureManager: ObservableObject {
    @Published var isCapturing: Bool = false
    @Published var currentAudioRoute: String = "Unknown"

    private var audioEngine: AVAudioEngine?
    private var inputNode: AVAudioInputNode?
    private var audioFormat: AVAudioFormat?

    /// Callback for captured audio buffers in CMSampleBuffer format (required by LiveKit)
    var onAudioBuffer: ((CMSampleBuffer) -> Void)?

    // MARK: - Audio Capture

    /// Start capturing audio from Bluetooth microphone
    func startCapture() throws {
        // Configure audio session for Bluetooth input
        let audioSession = AVAudioSession.sharedInstance()
        try audioSession.setCategory(
            .playAndRecord,
            mode: .default,
            options: [
                .allowBluetooth,
                .allowBluetoothA2DP,
                .defaultToSpeaker,
                .mixWithOthers // Allow TTS playback while capturing
            ]
        )
        try audioSession.setActive(true)

        // Setup audio engine to capture from Bluetooth microphone
        let engine = AVAudioEngine()
        self.audioEngine = engine

        let input = engine.inputNode
        self.inputNode = input

        let format = input.outputFormat(forBus: 0)
        self.audioFormat = format

        // Update current audio route
        updateCurrentRoute()

        // Install tap to capture audio buffers
        input.installTap(onBus: 0, bufferSize: 1024, format: format) { [weak self] buffer, time in
            guard let self = self else { return }

            // Convert AVAudioPCMBuffer to CMSampleBuffer
            if let sampleBuffer = self.convertToSampleBuffer(buffer: buffer, time: time) {
                Task { @MainActor in
                    self.onAudioBuffer?(sampleBuffer)
                }
            }
        }

        try engine.start()
        isCapturing = true
    }

    /// Stop capturing audio
    func stopCapture() {
        audioEngine?.stop()
        inputNode?.removeTap(onBus: 0)
        audioEngine = nil
        inputNode = nil
        audioFormat = nil
        isCapturing = false
    }

    // MARK: - Audio Route Monitoring

    private func updateCurrentRoute() {
        let audioSession = AVAudioSession.sharedInstance()
        let currentRoute = audioSession.currentRoute
        if let input = currentRoute.inputs.first {
            currentAudioRoute = input.portName
        } else {
            currentAudioRoute = "No Input"
        }
    }

    /// Get the current audio input device name
    func getCurrentInputDevice() -> String {
        let audioSession = AVAudioSession.sharedInstance()
        let currentRoute = audioSession.currentRoute
        if let input = currentRoute.inputs.first {
            return "\(input.portName) (\(input.portType.rawValue))"
        }
        return "No input device"
    }

    // MARK: - Buffer Conversion

    /// Convert AVAudioPCMBuffer to CMSampleBuffer (required format for LiveKit)
    private func convertToSampleBuffer(buffer: AVAudioPCMBuffer, time: AVAudioTime) -> CMSampleBuffer? {
        guard let formatDescription = createAudioFormatDescription(from: buffer.format) else {
            return nil
        }

        var sampleBuffer: CMSampleBuffer?
        var timing = CMSampleTimingInfo(
            duration: CMTime(value: CMTimeValue(buffer.frameLength), timescale: CMTimeScale(buffer.format.sampleRate)),
            presentationTimeStamp: convertAudioTimeToCMTime(time),
            decodeTimeStamp: .invalid
        )

        let status = CMSampleBufferCreate(
            allocator: kCFAllocatorDefault,
            dataBuffer: nil,
            dataReady: false,
            makeDataReadyCallback: nil,
            refcon: nil,
            formatDescription: formatDescription,
            sampleCount: CMItemCount(buffer.frameLength),
            sampleTimingEntryCount: 1,
            sampleTimingArray: &timing,
            sampleSizeEntryCount: 0,
            sampleSizeArray: nil,
            sampleBufferOut: &sampleBuffer
        )

        guard status == noErr, let sampleBuffer = sampleBuffer else {
            return nil
        }

        // Attach audio buffer list
        let audioBufferList = buffer.mutableAudioBufferList
        let status2 = CMSampleBufferSetDataBufferFromAudioBufferList(
            sampleBuffer,
            blockBufferAllocator: kCFAllocatorDefault,
            blockBufferMemoryAllocator: kCFAllocatorDefault,
            flags: 0,
            bufferList: audioBufferList
        )

        guard status2 == noErr else {
            return nil
        }

        return sampleBuffer
    }

    /// Create audio format description from AVAudioFormat
    private func createAudioFormatDescription(from format: AVAudioFormat) -> CMAudioFormatDescription? {
        var description: CMAudioFormatDescription?
        var streamDescription = format.streamDescription.pointee

        let status = CMAudioFormatDescriptionCreate(
            allocator: kCFAllocatorDefault,
            asbd: &streamDescription,
            layoutSize: 0,
            layout: nil,
            magicCookieSize: 0,
            magicCookie: nil,
            extensions: nil,
            formatDescriptionOut: &description
        )

        return status == noErr ? description : nil
    }

    /// Convert AVAudioTime to CMTime
    private func convertAudioTimeToCMTime(_ audioTime: AVAudioTime) -> CMTime {
        if audioTime.isSampleTimeValid {
            return CMTime(
                value: audioTime.sampleTime,
                timescale: CMTimeScale(audioTime.sampleRate)
            )
        } else if audioTime.isHostTimeValid {
            return CMTime(
                seconds: AVAudioTime.seconds(forHostTime: audioTime.hostTime),
                preferredTimescale: 1000000000
            )
        } else {
            return .zero
        }
    }

    // MARK: - Permissions

    /// Request microphone permission
    static func requestMicrophonePermission() async -> Bool {
        return await withCheckedContinuation { continuation in
            AVAudioSession.sharedInstance().requestRecordPermission { granted in
                continuation.resume(returning: granted)
            }
        }
    }

    /// Check if microphone permission is granted
    static var hasMicrophonePermission: Bool {
        return AVAudioSession.sharedInstance().recordPermission == .granted
    }
}
