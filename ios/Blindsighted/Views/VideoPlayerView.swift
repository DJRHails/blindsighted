//
// VideoPlayerView.swift
//
// Full-screen video player for playback of recorded videos from the gallery.
// Uses AVPlayer for smooth playback with standard controls.
//

import SwiftUI
import AVKit

struct VideoPlayerView: View {
  let video: RecordedVideo
  @Environment(\.dismiss) private var dismiss
  @State private var player: AVPlayer?
  @State private var showShareSheet = false

  var body: some View {
    ZStack {
      Color.black.ignoresSafeArea()

      if let player = player {
        VideoPlayer(player: player)
          .ignoresSafeArea()
          .onAppear {
            player.play()
          }
          .onDisappear {
            player.pause()
          }
      } else {
        ProgressView()
          .scaleEffect(1.5)
          .tint(.white)
      }

      // Custom overlay controls
      VStack {
        HStack {
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

          Spacer()

          Button(action: {
            showShareSheet = true
          }) {
            Image(systemName: "square.and.arrow.up")
              .font(.title3)
              .fontWeight(.semibold)
              .foregroundColor(.white)
              .padding(12)
              .background(Color.black.opacity(0.5))
              .clipShape(Circle())
          }
        }
        .padding()

        Spacer()

        // Video info
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
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding()
        .background(
          LinearGradient(
            colors: [Color.black.opacity(0.6), Color.clear],
            startPoint: .bottom,
            endPoint: .top
          )
        )
      }
    }
    .onAppear {
      setupPlayer()
    }
    .sheet(isPresented: $showShareSheet) {
      ShareSheet(video: video)
    }
  }

  private func setupPlayer() {
    let playerItem = AVPlayerItem(url: video.url)
    let avPlayer = AVPlayer(playerItem: playerItem)
    self.player = avPlayer

    // Loop video
    NotificationCenter.default.addObserver(
      forName: .AVPlayerItemDidPlayToEndTime,
      object: playerItem,
      queue: .main
    ) { _ in
      avPlayer.seek(to: .zero)
      avPlayer.play()
    }
  }
}

struct ShareSheet: UIViewControllerRepresentable {
  let video: RecordedVideo

  func makeUIViewController(context: Context) -> UIActivityViewController {
    let activityViewController = UIActivityViewController(
      activityItems: [video.url],
      applicationActivities: nil
    )

    return activityViewController
  }

  func updateUIViewController(_ uiViewController: UIActivityViewController, context: Context) {
    // No updates needed
  }
}
