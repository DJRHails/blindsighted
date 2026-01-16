//
// StreamView.swift
//
// Main UI for video streaming from Meta wearable devices using the DAT SDK.
// This view demonstrates the complete streaming API: video streaming with real-time display, photo capture,
// and error handling.
//

import MWDATCore
import SwiftUI

struct StreamView: View {
  @ObservedObject var viewModel: StreamSessionViewModel
  @ObservedObject var wearablesVM: WearablesViewModel

  var body: some View {
    ZStack {
      // Black background for letterboxing/pillarboxing
      Color.black
        .edgesIgnoringSafeArea(.all)

      // Video backdrop
      if let videoFrame = viewModel.currentVideoFrame, viewModel.hasReceivedFirstFrame {
        GeometryReader { geometry in
          Image(uiImage: videoFrame)
            .resizable()
            .aspectRatio(contentMode: .fit)
            .frame(width: geometry.size.width, height: geometry.size.height)
            .accessibilityLabel("Live video stream from glasses")
            .accessibilityAddTraits(.isImage)
        }
        .edgesIgnoringSafeArea(.all)
      } else {
        ProgressView()
          .scaleEffect(1.5)
          .foregroundColor(.white)
          .accessibilityLabel("Waiting for video stream")
      }

      // Top-left: Recording indicator
      if viewModel.isStreaming {
        VStack {
          HStack {
            HStack(spacing: 6) {
              Circle()
                .fill(Color.red)
                .frame(width: 12, height: 12)
                .accessibilityHidden(true)
              Text(viewModel.recordingDuration.formattedDuration)
                .font(.system(size: 14, weight: .medium))
                .foregroundColor(.white)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.black.opacity(0.5))
            .cornerRadius(16)
            .accessibilityElement(children: .combine)
            .accessibilityLabel("Recording")
            .accessibilityValue(viewModel.recordingDuration.formattedDuration)
            .accessibilityAddTraits(.updatesFrequently)
            Spacer()
          }
          Spacer()
        }
        .padding(.all, 24)
      }

      // Top-right: LiveKit connection indicator
      if viewModel.isLiveKitConnected {
        VStack {
          HStack {
            Spacer()
            HStack(spacing: 6) {
              Circle()
                .fill(Color.green)
                .frame(width: 12, height: 12)
                .accessibilityHidden(true)
              Text("LIVE")
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(.white)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.black.opacity(0.5))
            .cornerRadius(16)
            .accessibilityElement(children: .combine)
            .accessibilityLabel("LiveKit connection status: Live")
          }
          Spacer()
        }
        .padding(.all, 24)
      }

      // Bottom controls layer
      VStack {
        Spacer()
        ControlsView(viewModel: viewModel)
      }
      .padding(.all, 24)
    }
    // Show captured photos from DAT SDK in a preview sheet
    .sheet(isPresented: $viewModel.showPhotoPreview) {
      if let photo = viewModel.capturedPhoto {
        PhotoPreviewView(
          photo: photo,
          onDismiss: {
            viewModel.dismissPhotoPreview()
          }
        )
      }
    }
  }
}// Extracted controls for clarity
struct ControlsView: View {
  @ObservedObject var viewModel: StreamSessionViewModel
  var body: some View {
    // Controls row
    HStack(spacing: 8) {
      CustomButton(
        title: "Stop recording",
        style: .destructive,
        isDisabled: false
      ) {
        Task {
          await viewModel.stopSession()
        }
      }
      .accessibilityHint("Stops video recording and returns to home screen")

      // Photo button
      CircleButton(
        icon: "camera.fill",
        text: nil,
        accessibilityLabel: "Capture photo",
        accessibilityHint: "Takes a photo from your glasses camera"
      ) {
        viewModel.capturePhoto()
      }

      // Mute button - only show when LiveKit is connected
      if viewModel.isLiveKitConnected {
        CircleButton(
          icon: viewModel.isMicrophoneMuted ? "mic.slash.fill" : "mic.fill",
          text: nil,
          accessibilityLabel: viewModel.isMicrophoneMuted ? "Unmute microphone" : "Mute microphone",
          accessibilityHint: viewModel.isMicrophoneMuted ? "Turns on your microphone" : "Turns off your microphone"
        ) {
          Task {
            await viewModel.toggleMicrophone()
          }
        }
      }
    }
    .accessibilityElement(children: .contain)
    .accessibilityLabel("Recording controls")
  }
}
