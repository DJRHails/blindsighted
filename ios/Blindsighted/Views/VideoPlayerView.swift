//
// VideoPlayerView.swift
//
// Full-screen video player for playback of recorded videos from the gallery.
// Uses AVPlayer for smooth playback with custom controls.
//

import SwiftUI
import AVKit
import AVFoundation

struct VideoPlayerView: View {
  let video: RecordedVideo
  @Environment(\.dismiss) private var dismiss
  @State private var player: AVPlayer?
  @State private var isPaused: Bool = true
  @State private var showControls: Bool = true
  @State private var hideControlsTask: Task<Void, Never>?
  @State private var currentTime: Double = 0
  @State private var duration: Double = 0
  @State private var isScrubbing: Bool = false

  var body: some View {
    ZStack {
      Color.black.ignoresSafeArea()

      if let player = player {
        CustomVideoPlayerView(player: player)
          .ignoresSafeArea()
          .onAppear {
            player.play()
          }
          .onDisappear {
            player.pause()
            hideControlsTask?.cancel()
          }
      } else {
        ProgressView()
          .scaleEffect(1.5)
          .tint(.white)
      }

      // Custom overlay controls
      VStack {
        // Top controls - close and share buttons
        HStack {
          Spacer()

          ShareLink(item: video.url) {
            Image(systemName: "square.and.arrow.up")
              .font(.title3)
              .fontWeight(.semibold)
              .foregroundColor(.white)
              .padding(12)
              .background(Color.black.opacity(0.5))
              .clipShape(Circle())
          }

          Button(action: {
            dismiss()
          }) {
            Image(systemName: "xmark")
              .font(.title3)
              .fontWeight(.semibold)
              .foregroundColor(.white)
              .padding(12)
              .background(Color.black.opacity(0.5))
              .clipShape(Circle())
          }
        }
        .padding()
        .opacity(showControls ? 1 : 0)

        Spacer()

        // Bottom gradient with video info
        VStack(alignment: .leading, spacing: 4) {
          Text(video.recordedAt, style: .date)
            .font(.subheadline)
            .fontWeight(.semibold)
            .foregroundColor(.white)

          HStack {
            Text(video.duration.formattedDuration)
              .font(.caption)
              .foregroundColor(.white.opacity(0.8))

            Text("•")
              .foregroundColor(.white.opacity(0.8))

            Text(video.fileSize.formattedFileSize)
              .font(.caption)
              .foregroundColor(.white.opacity(0.8))
          }

          // Location info if available
          if let locationDesc = video.locationDescription {
            HStack(spacing: 4) {
              Image(systemName: "location.fill")
                .font(.caption)
                .foregroundColor(.white.opacity(0.8))
              Text(locationDesc)
                .font(.caption)
                .foregroundColor(.white.opacity(0.8))
            }
          }

          // Scrub bar
          HStack(spacing: 12) {
            Text(formatTime(currentTime))
              .font(.caption)
              .foregroundColor(.white.opacity(0.8))
              .monospacedDigit()

            Slider(
              value: Binding(
                get: { currentTime },
                set: { newValue in
                  currentTime = newValue
                  isScrubbing = true
                  player?.seek(to: CMTime(seconds: newValue, preferredTimescale: 600))
                  isScrubbing = false
                }
              ),
              in: 0...max(duration, 0.1)
            )
            .tint(.white)

            Text(formatTime(duration))
              .font(.caption)
              .foregroundColor(.white.opacity(0.8))
              .monospacedDigit()
          }
          .padding(.top, 4)

          // Play/Pause button
          HStack {
            Spacer()

            Button(action: {
              if isPaused {
                player?.play()
              } else {
                player?.pause()
              }
            }) {
              Image(systemName: isPaused ? "play.fill" : "pause.fill")
                .font(.title2)
                .foregroundColor(.white)
                .frame(width: 44, height: 44)
                .background(Color.white.opacity(0.2))
                .clipShape(Circle())
            }

            Spacer()
          }
          .padding(.top, 8)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .padding(.bottom, 8)
        .background(
          LinearGradient(
            colors: [Color.black.opacity(0.7), Color.black.opacity(0.3), Color.clear],
            startPoint: .bottom,
            endPoint: .top
          )
          .ignoresSafeArea(edges: .bottom)
        )
        .opacity(showControls ? 1 : 0)
        .transition(.opacity)
      }
    }
    .onAppear {
      setupPlayer()
    }
    .onTapGesture {
      withAnimation(.easeInOut(duration: 0.2)) {
        showControls.toggle()
      }
      scheduleHideControls()
    }
  }

  private func setupPlayer() {
    let playerItem = AVPlayerItem(url: video.url)
    let avPlayer = AVPlayer(playerItem: playerItem)
    self.player = avPlayer

    // Get video duration
    Task {
      if let duration = try? await playerItem.asset.load(.duration) {
        self.duration = duration.seconds
      }
    }

    // Observe playback rate and current time
    avPlayer.addPeriodicTimeObserver(
      forInterval: CMTime(seconds: 0.1, preferredTimescale: 600),
      queue: .main
    ) { [self, weak avPlayer] time in
      guard let player = avPlayer else { return }

      // Update current time if not scrubbing
      if !self.isScrubbing {
        self.currentTime = time.seconds
      }

      let wasPlaying = !self.isPaused
      self.isPaused = player.rate == 0

      // Show controls when video is paused
      if self.isPaused && !wasPlaying {
        withAnimation(.easeInOut(duration: 0.2)) {
          self.showControls = true
        }
      } else if !self.isPaused && self.showControls {
        self.scheduleHideControls()
      }
    }

    // Loop video
    NotificationCenter.default.addObserver(
      forName: .AVPlayerItemDidPlayToEndTime,
      object: playerItem,
      queue: .main
    ) { _ in
      avPlayer.seek(to: CMTime.zero)
      avPlayer.play()
    }
  }

  private func scheduleHideControls() {
    hideControlsTask?.cancel()
    hideControlsTask = Task {
      try? await Task.sleep(nanoseconds: 3_000_000_000) // 3 seconds
      guard !Task.isCancelled, !isPaused else { return }
      withAnimation(.easeInOut(duration: 0.2)) {
        showControls = false
      }
    }
  }

  private func formatTime(_ seconds: Double) -> String {
    guard seconds.isFinite && !seconds.isNaN else { return "0:00" }
    let totalSeconds = Int(seconds)
    let minutes = totalSeconds / 60
    let remainingSeconds = totalSeconds % 60
    return String(format: "%d:%02d", minutes, remainingSeconds)
  }
}

// MARK: - Custom Video Player View

/// Custom video player using AVPlayerLayer for full control without built-in controls
struct CustomVideoPlayerView: UIViewRepresentable {
  let player: AVPlayer

  func makeUIView(context: Context) -> UIView {
    let view = VideoPlayerUIView()
    view.player = player
    return view
  }

  func updateUIView(_ uiView: UIView, context: Context) {
    // No updates needed
  }
}

class VideoPlayerUIView: UIView {
  var player: AVPlayer? {
    didSet {
      playerLayer.player = player
    }
  }

  override class var layerClass: AnyClass {
    AVPlayerLayer.self
  }

  var playerLayer: AVPlayerLayer {
    layer as! AVPlayerLayer
  }

  override init(frame: CGRect) {
    super.init(frame: frame)
    playerLayer.videoGravity = .resizeAspect
  }

  required init?(coder: NSCoder) {
    fatalError("init(coder:) has not been implemented")
  }
}
