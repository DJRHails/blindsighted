//
// PhotoPreviewView.swift
//
// UI for previewing and sharing photos captured from Meta wearable devices via the DAT SDK.
// This view displays photos captured using StreamSession.capturePhoto() and provides sharing
// functionality.
//

import SwiftUI
import UIKit  // Only for UIImage data model

struct PhotoPreviewView: View {
  let photo: UIImage
  let onDismiss: () -> Void

  @State private var dragOffset = CGSize.zero
  @State private var screenHeight: CGFloat = 0

  var body: some View {
    GeometryReader { geometry in
      ZStack {
        // Semi-transparent background overlay
        Color.black.opacity(0.8)
          .ignoresSafeArea()
          .onTapGesture {
            dismissWithAnimation()
          }

        VStack(spacing: 20) {
          Spacer()

          photoDisplayView(geometry: geometry)

          // Share button using SwiftUI ShareLink
          if let imageData = photo.jpegData(compressionQuality: 0.9) {
            ShareLink(
              item: Image(uiImage: photo),
              preview: SharePreview("Photo", image: Image(uiImage: photo))
            ) {
              Label("Share", systemImage: "square.and.arrow.up")
                .font(.headline)
                .foregroundColor(.white)
                .padding()
                .background(Color.blue)
                .cornerRadius(12)
            }
          }

          Button("Close") {
            dismissWithAnimation()
          }
          .font(.headline)
          .foregroundColor(.white)
          .padding()
          .background(Color.gray.opacity(0.5))
          .cornerRadius(12)

          Spacer()
        }
        .padding()
        .offset(dragOffset)
        .animation(.spring(response: 0.6, dampingFraction: 0.8), value: dragOffset)
      }
      .onAppear {
        screenHeight = geometry.size.height
      }
    }
  }

  private func photoDisplayView(geometry: GeometryProxy) -> some View {
    Image(uiImage: photo)
      .resizable()
      .aspectRatio(contentMode: .fit)
      .frame(maxWidth: geometry.size.width, maxHeight: geometry.size.height * 0.6)
      .cornerRadius(12)
      .shadow(color: .black.opacity(0.3), radius: 10, x: 0, y: 5)
      .gesture(
        DragGesture()
          .onChanged { value in
            dragOffset = value.translation
          }
          .onEnded { value in
            if abs(value.translation.height) > 100 {
              dismissWithAnimation()
            } else {
              withAnimation(.spring()) {
                dragOffset = .zero
              }
            }
          }
      )
  }

  private func dismissWithAnimation() {
    withAnimation(.easeInOut(duration: 0.3)) {
      dragOffset = CGSize(width: 0, height: screenHeight)
    }
    Task {
      try? await Task.sleep(nanoseconds: 300_000_000)
      onDismiss()
    }
  }
}
