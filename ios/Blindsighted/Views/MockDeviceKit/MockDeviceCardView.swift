//
// MockDeviceCardView.swift
//
// UI component for managing individual mock Meta wearable devices during development.
// This card provides controls for simulating device states (power, wearing, folding)
// and loading mock media content for testing DAT SDK streaming and photo capture features.
// Useful for testing without requiring physical Meta hardware.
//

#if DEBUG

import PhotosUI
import SwiftUI

struct MockDeviceCardView: View {
  @ObservedObject var viewModel: ViewModel
  let onUnpairDevice: () -> Void
  @State private var selectedVideoItem: PhotosPickerItem?
  @State private var selectedImageItem: PhotosPickerItem?

  var body: some View {
    CardView {
      VStack(spacing: 8) {
        HStack {
          VStack(alignment: .leading, spacing: 4) {
            Text(viewModel.deviceName)
              .font(.headline)
              .foregroundColor(.primary)
              .lineLimit(1)
            Text(viewModel.id)
              .font(.caption)
              .foregroundColor(.secondary)
              .lineLimit(1)
              .truncationMode(.middle)
          }

          Spacer()

          MockDeviceKitButton("Unpair", style: .destructive, expandsHorizontally: false) {
            onUnpairDevice()
          }
        }

        Divider()

        VStack(spacing: 8) {
          HStack(spacing: 8) {
            MockDeviceKitButton("Power On") {
              viewModel.powerOn()
            }

            MockDeviceKitButton("Power Off") {
              viewModel.powerOff()
            }
          }

          HStack(spacing: 8) {
            MockDeviceKitButton("Don") {
              viewModel.don()
            }

            MockDeviceKitButton("Doff") {
              viewModel.doff()
            }
          }

          HStack(spacing: 8) {
            MockDeviceKitButton("Unfold") {
              viewModel.unfold()
            }

            MockDeviceKitButton("Fold") {
              viewModel.fold()
            }
          }

          HStack(spacing: 8) {
            PhotosPicker(
              selection: $selectedVideoItem,
              matching: .videos
            ) {
              Text("Select video")
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundColor(.blue)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
                .background(Color.blue.opacity(0.1))
                .cornerRadius(8)
            }
            .onChange(of: selectedVideoItem) { _, newItem in
              Task {
                if let newItem,
                   let data = try? await newItem.loadTransferable(type: Data.self) {
                  let tempURL = FileManager.default.temporaryDirectory
                    .appendingPathComponent(UUID().uuidString)
                    .appendingPathExtension("mp4")
                  try? data.write(to: tempURL)
                  viewModel.selectVideo(from: tempURL)
                }
              }
            }

            StatusText(
              isActive: viewModel.hasCameraFeed,
              activeText: "Has camera feed",
              inactiveText: "No camera feed"
            )
          }

          HStack(spacing: 8) {
            PhotosPicker(
              selection: $selectedImageItem,
              matching: .images
            ) {
              Text("Select image")
                .font(.subheadline)
                .fontWeight(.medium)
                .foregroundColor(.blue)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 8)
                .background(Color.blue.opacity(0.1))
                .cornerRadius(8)
            }
            .onChange(of: selectedImageItem) { _, newItem in
              Task {
                if let newItem,
                   let data = try? await newItem.loadTransferable(type: Data.self) {
                  let tempURL = FileManager.default.temporaryDirectory
                    .appendingPathComponent(UUID().uuidString)
                    .appendingPathExtension("jpg")
                  try? data.write(to: tempURL)
                  viewModel.selectImage(from: tempURL)
                }
              }
            }

            StatusText(
              isActive: viewModel.hasCapturedImage,
              activeText: "Has captured image",
              inactiveText: "No captured image"
            )
          }
        }
      }
      .padding()
    }
  }
}

#endif
