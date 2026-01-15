//
// VideoGalleryView.swift
//
// Gallery view for browsing and managing recorded videos from Meta wearable devices.
// Displays videos in a grid with thumbnails, duration, and file size information.
//

import SwiftUI

struct VideoGalleryView: View {
  @StateObject private var viewModel = VideoGalleryViewModel()
  @State private var selectedVideo: RecordedVideo?

  private let columns = [
    GridItem(.flexible(), spacing: 12),
    GridItem(.flexible(), spacing: 12),
  ]

  var body: some View {
    NavigationView {
      ZStack {
        if viewModel.videos.isEmpty && !viewModel.isLoading {
          emptyStateView
        } else {
          ScrollView {
            LazyVGrid(columns: columns, spacing: 12) {
              ForEach(viewModel.videos) { video in
                VideoThumbnailCard(
                  video: video,
                  thumbnail: viewModel.thumbnails[video.id]
                )
                .onTapGesture {
                  selectedVideo = video
                }
                .contextMenu {
                  Button(role: .destructive) {
                    viewModel.deleteVideo(video)
                  } label: {
                    Label("Delete", systemImage: "trash")
                  }
                }
              }
            }
            .padding()
          }
        }

        if viewModel.isLoading {
          ProgressView()
            .scaleEffect(1.5)
        }
      }
      .navigationTitle("Gallery")
      .navigationBarTitleDisplayMode(.large)
      .toolbar {
        ToolbarItem(placement: .navigationBarTrailing) {
          Menu {
            Text("Storage: \(viewModel.totalStorage)")
            Button(role: .destructive, action: {
              // Delete all - could add confirmation dialog
            }) {
              Label("Delete All", systemImage: "trash.fill")
            }
          } label: {
            Image(systemName: "ellipsis.circle")
          }
        }
      }
      .sheet(item: $selectedVideo) { video in
        VideoPlayerView(video: video)
      }
      .alert("Error", isPresented: $viewModel.showError) {
        Button("OK") {
          viewModel.dismissError()
        }
      } message: {
        Text(viewModel.errorMessage)
      }
      .onAppear {
        viewModel.loadVideos()
      }
    }
  }

  private var emptyStateView: some View {
    VStack(spacing: 16) {
      Image(systemName: "video.slash")
        .font(.system(size: 60))
        .foregroundColor(.gray)

      Text("No Recordings")
        .font(.title2)
        .fontWeight(.semibold)

      Text("Start streaming and tap the record button to save videos")
        .font(.subheadline)
        .foregroundColor(.secondary)
        .multilineTextAlignment(.center)
        .padding(.horizontal, 40)
    }
  }
}

struct VideoThumbnailCard: View {
  let video: RecordedVideo
  let thumbnail: UIImage?

  var body: some View {
    VStack(alignment: .leading, spacing: 8) {
      // Thumbnail
      ZStack(alignment: .bottomTrailing) {
        if let thumbnail = thumbnail {
          Image(uiImage: thumbnail)
            .resizable()
            .aspectRatio(contentMode: .fill)
            .frame(height: 180)
            .clipped()
            .cornerRadius(12)
        } else {
          Rectangle()
            .fill(Color.gray.opacity(0.3))
            .frame(height: 180)
            .cornerRadius(12)
            .overlay(
              ProgressView()
            )
        }

        // Duration badge
        Text(video.duration.formattedDuration)
          .font(.caption2)
          .fontWeight(.semibold)
          .foregroundColor(.white)
          .padding(.horizontal, 6)
          .padding(.vertical, 3)
          .background(Color.black.opacity(0.7))
          .cornerRadius(4)
          .padding(8)
      }

      // Video info
      VStack(alignment: .leading, spacing: 4) {
        Text(video.recordedAt, style: .date)
          .font(.caption)
          .fontWeight(.medium)

        HStack {
          Text(video.recordedAt, style: .time)
            .font(.caption2)
            .foregroundColor(.secondary)

          Spacer()

          Text(video.fileSize.formattedFileSize)
            .font(.caption2)
            .foregroundColor(.secondary)
        }
      }
    }
  }
}
