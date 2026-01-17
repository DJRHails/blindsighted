//
// PhotoGalleryViewModel.swift
//
// View model for managing the photo gallery, displaying all periodic photos captured during recordings.
//

import Foundation
import SwiftUI

@MainActor
class PhotoGalleryViewModel: ObservableObject {
  @Published var photos: [CapturedPhoto] = []
  @Published var thumbnails: [UUID: UIImage] = [:]
  @Published var selectedPhoto: CapturedPhoto?
  @Published var isLoading: Bool = false
  @Published var showError: Bool = false
  @Published var errorMessage: String = ""
  @Published var totalStorage: String = "0 MB"
  @Published var showDeleteAllConfirmation: Bool = false

  private let fileManager = PhotoFileManager.shared

  init() {
    loadPhotos()
  }

  func loadPhotos() {
    isLoading = true

    Task {
      do {
        photos = try fileManager.listPhotos()
        updateTotalStorage()
        await loadThumbnails()
        isLoading = false
      } catch {
        showError("Failed to load photos: \(error.localizedDescription)")
        isLoading = false
      }
    }
  }

  private func updateTotalStorage() {
    do {
      let bytes = try fileManager.totalStorageUsed()
      totalStorage = bytes.formattedFileSize
    } catch {
      totalStorage = "Unknown"
    }
  }

  private func loadThumbnails() async {
    // Load thumbnails for visible photos (limit to first 100 for performance)
    for photo in photos.prefix(100) {
      if thumbnails[photo.id] == nil {
        if let image = fileManager.loadImage(for: photo) {
          // Create smaller thumbnail for grid display
          let thumbnail = await createThumbnail(from: image, maxSize: 200)
          thumbnails[photo.id] = thumbnail
        }
      }
    }
  }

  private func createThumbnail(from image: UIImage, maxSize: CGFloat) async -> UIImage {
    let scale = min(maxSize / image.size.width, maxSize / image.size.height)
    let newSize = CGSize(width: image.size.width * scale, height: image.size.height * scale)

    let renderer = UIGraphicsImageRenderer(size: newSize)
    return renderer.image { _ in
      image.draw(in: CGRect(origin: .zero, size: newSize))
    }
  }

  func deletePhoto(_ photo: CapturedPhoto) {
    do {
      try fileManager.deletePhoto(photo)
      photos.removeAll { $0.id == photo.id }
      thumbnails.removeValue(forKey: photo.id)
      updateTotalStorage()

      if selectedPhoto?.id == photo.id {
        selectedPhoto = nil
      }
    } catch {
      showError("Failed to delete photo: \(error.localizedDescription)")
    }
  }

  func deleteAllPhotos() {
    do {
      try fileManager.deleteAllPhotos()
      photos.removeAll()
      thumbnails.removeAll()
      selectedPhoto = nil
      updateTotalStorage()
    } catch {
      showError("Failed to delete photos: \(error.localizedDescription)")
    }
  }

  func loadFullImage(for photo: CapturedPhoto) -> UIImage? {
    return fileManager.loadImage(for: photo)
  }

  private func showError(_ message: String) {
    errorMessage = message
    showError = true
  }

  /// Get the directory path for Files app access
  var photosDirectoryPath: String {
    fileManager.directoryURL.path
  }
}
