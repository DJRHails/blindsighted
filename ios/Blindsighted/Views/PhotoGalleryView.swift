//
// PhotoGalleryView.swift
//
// Photo gallery view for browsing all periodic photos captured during recording sessions.
// Displays photos in a grid layout with full-size preview on tap.
//

import SwiftUI

struct PhotoGalleryView: View {
  @StateObject private var viewModel = PhotoGalleryViewModel()
  @State private var showFullPhoto: Bool = false

  private let columns = [
    GridItem(.flexible(), spacing: 2),
    GridItem(.flexible(), spacing: 2),
    GridItem(.flexible(), spacing: 2)
  ]

  var body: some View {
    NavigationView {
      ScrollView {
        if viewModel.photos.isEmpty && !viewModel.isLoading {
          emptyStateView
        } else {
          LazyVGrid(columns: columns, spacing: 2) {
            ForEach(viewModel.photos) { photo in
              photoCell(photo)
            }
          }
          .padding(2)
        }
      }
      .background(Color(UIColor.systemBackground))
      .navigationTitle("Photos")
      .navigationBarTitleDisplayMode(.large)
      .toolbar {
        ToolbarItem(placement: .navigationBarTrailing) {
          Menu {
            Text("\(viewModel.photos.count) photos")
            Text("Storage: \(viewModel.totalStorage)")
            Divider()
            Button(role: .destructive, action: {
              viewModel.showDeleteAllConfirmation = true
            }) {
              Label("Delete All Photos", systemImage: "trash.fill")
            }
            .disabled(viewModel.photos.isEmpty)
          } label: {
            Image(systemName: "ellipsis.circle")
          }
          .accessibilityLabel("Options menu")
          .accessibilityHint("Opens photo count, storage info, and deletion options")
        }
      }
      .refreshable {
        viewModel.loadPhotos()
      }
      .alert("Error", isPresented: $viewModel.showError) {
        Button("OK") {}
      } message: {
        Text(viewModel.errorMessage)
      }
      .confirmationDialog(
        "Delete All Photos?",
        isPresented: $viewModel.showDeleteAllConfirmation,
        titleVisibility: .visible
      ) {
        Button("Delete All", role: .destructive) {
          viewModel.deleteAllPhotos()
        }
        Button("Cancel", role: .cancel) {}
      } message: {
        Text("This will permanently delete all \(viewModel.photos.count) photos. This action cannot be undone.")
      }
      .sheet(item: $viewModel.selectedPhoto) { photo in
        PhotoDetailView(photo: photo, viewModel: viewModel)
      }
      .overlay {
        if viewModel.isLoading && viewModel.photos.isEmpty {
          ProgressView()
            .scaleEffect(1.5)
            .accessibilityLabel("Loading photos")
        }
      }
    }
  }

  @ViewBuilder
  private func photoCell(_ photo: CapturedPhoto) -> some View {
    Button {
      viewModel.selectedPhoto = photo
    } label: {
      ZStack {
        if let thumbnail = viewModel.thumbnails[photo.id] {
          Image(uiImage: thumbnail)
            .resizable()
            .aspectRatio(1, contentMode: .fill)
            .clipped()
        } else {
          Rectangle()
            .fill(Color.gray.opacity(0.3))
            .aspectRatio(1, contentMode: .fill)
            .overlay {
              ProgressView()
                .scaleEffect(0.8)
            }
        }
      }
    }
    .buttonStyle(.plain)
    .accessibilityLabel("Photo from \(formatDateTime(photo.capturedAt))")
    .accessibilityHint("Double tap to view full size")
    .contextMenu {
      Button {
        viewModel.selectedPhoto = photo
      } label: {
        Label("View Photo", systemImage: "eye")
      }
      Button(role: .destructive) {
        viewModel.deletePhoto(photo)
      } label: {
        Label("Delete", systemImage: "trash")
      }
    }
  }

  private func formatDateTime(_ date: Date) -> String {
    let formatter = DateFormatter()
    formatter.dateStyle = .medium
    formatter.timeStyle = .short
    return formatter.string(from: date)
  }

  private var emptyStateView: some View {
    VStack(spacing: 16) {
      Image(systemName: "photo.on.rectangle.angled")
        .font(.system(size: 60))
        .foregroundColor(.secondary)
        .accessibilityHidden(true)

      Text("No Photos")
        .font(.title2)
        .fontWeight(.semibold)

      Text("Photos are automatically captured every second during recording")
        .font(.subheadline)
        .foregroundColor(.secondary)
        .multilineTextAlignment(.center)
        .padding(.horizontal, 40)
    }
    .frame(maxWidth: .infinity, maxHeight: .infinity)
    .padding(.top, 100)
  }
}

// MARK: - Photo Detail View

struct PhotoDetailView: View {
  let photo: CapturedPhoto
  @ObservedObject var viewModel: PhotoGalleryViewModel
  @Environment(\.dismiss) private var dismiss
  @State private var fullImage: UIImage?

  var body: some View {
    NavigationView {
      GeometryReader { geometry in
        ZStack {
          Color.black.ignoresSafeArea()

          if let image = fullImage {
            Image(uiImage: image)
              .resizable()
              .aspectRatio(contentMode: .fit)
              .frame(maxWidth: geometry.size.width, maxHeight: geometry.size.height)
              .accessibilityLabel("Full size photo from \(formatDateTime(photo.capturedAt))")
          } else {
            ProgressView()
              .scaleEffect(1.5)
              .tint(.white)
              .accessibilityLabel("Loading full size photo")
          }
        }
      }
      .navigationBarTitleDisplayMode(.inline)
      .toolbar {
        ToolbarItem(placement: .navigationBarLeading) {
          Button("Done") {
            dismiss()
          }
          .foregroundColor(.white)
        }

        ToolbarItem(placement: .principal) {
          VStack(spacing: 2) {
            Text(formatDate(photo.capturedAt))
              .font(.subheadline)
              .fontWeight(.semibold)
            Text(formatTime(photo.capturedAt))
              .font(.caption)
              .foregroundColor(.secondary)
          }
          .foregroundColor(.white)
        }

        ToolbarItem(placement: .navigationBarTrailing) {
          if let image = fullImage {
            ShareLink(item: Image(uiImage: image), preview: SharePreview("Photo", image: Image(uiImage: image))) {
              Image(systemName: "square.and.arrow.up")
                .foregroundColor(.white)
            }
            .accessibilityLabel("Share photo")
            .accessibilityHint("Opens share options for this photo")
          }
        }
      }
      .toolbarBackground(.black, for: .navigationBar)
      .toolbarBackground(.visible, for: .navigationBar)
    }
    .task {
      fullImage = viewModel.loadFullImage(for: photo)
    }
  }

  private func formatDate(_ date: Date) -> String {
    let formatter = DateFormatter()
    formatter.dateStyle = .medium
    formatter.timeStyle = .none
    return formatter.string(from: date)
  }

  private func formatTime(_ date: Date) -> String {
    let formatter = DateFormatter()
    formatter.dateStyle = .none
    formatter.timeStyle = .medium
    return formatter.string(from: date)
  }

  private func formatDateTime(_ date: Date) -> String {
    let formatter = DateFormatter()
    formatter.dateStyle = .medium
    formatter.timeStyle = .short
    return formatter.string(from: date)
  }
}

#if DEBUG
#Preview("Empty State") {
  PhotoGalleryView()
}
#endif
