//
// VideoGalleryViewModel.swift
//
// View model for managing the video gallery, including listing, deleting, and
// generating thumbnails for recorded videos.
//

import Foundation
import SwiftUI

@MainActor
class VideoGalleryViewModel: ObservableObject {
  @Published var videos: [RecordedVideo] = []
  @Published var thumbnails: [UUID: UIImage] = [:]
  @Published var isLoading: Bool = false
  @Published var showError: Bool = false
  @Published var errorMessage: String = ""
  @Published var totalStorage: String = "0 MB"

  private let fileManager = VideoFileManager.shared

  init() {
    loadVideos()
  }

  func loadVideos() {
    isLoading = true

    Task {
      do {
        videos = try fileManager.listVideos()
        try updateTotalStorage()

        // Generate thumbnails for visible videos
        for video in videos.prefix(20) {
          await generateThumbnail(for: video)
        }

        isLoading = false
      } catch {
        showError("Failed to load videos: \(error.localizedDescription)")
        isLoading = false
      }
    }
  }

  func generateThumbnail(for video: RecordedVideo) async {
    guard thumbnails[video.id] == nil else { return }

    if let thumbnail = await fileManager.generateThumbnail(for: video) {
      thumbnails[video.id] = thumbnail
    }
  }

  func deleteVideo(_ video: RecordedVideo) {
    do {
      try fileManager.deleteVideo(video)
      videos.removeAll { $0.id == video.id }
      thumbnails.removeValue(forKey: video.id)
      try? updateTotalStorage()
    } catch {
      showError("Failed to delete video: \(error.localizedDescription)")
    }
  }

  func deleteVideos(at offsets: IndexSet) {
    for index in offsets {
      let video = videos[index]
      deleteVideo(video)
    }
  }

  private func updateTotalStorage() throws {
    let bytes = try fileManager.totalStorageUsed()
    totalStorage = bytes.formattedFileSize
  }

  private func showError(_ message: String) {
    errorMessage = message
    showError = true
  }

  func dismissError() {
    showError = false
    errorMessage = ""
  }
}
