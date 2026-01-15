//
// VideoFileManager.swift
//
// Manages video file storage and retrieval in the app's Documents directory.
// Handles file naming, directory creation, and file list management.
//

import Foundation
import AVFoundation
import UIKit

let VIDEOS_DIRECTORY = "BlindsightedLifelog"

struct RecordedVideo: Identifiable, Codable {
  let id: UUID
  let filename: String
  let recordedAt: Date
  let duration: TimeInterval
  let fileSize: Int64

  var url: URL {
    VideoFileManager.shared.videoURL(for: filename)
  }
}

class VideoFileManager {
  static let shared = VideoFileManager()

  private let videosDirectory: URL

  private init() {
    let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    self.videosDirectory = documentsPath.appendingPathComponent(VIDEOS_DIRECTORY, isDirectory: true)

    // Create videos directory if it doesn't exist
    try? FileManager.default.createDirectory(
      at: videosDirectory,
      withIntermediateDirectories: true,
      attributes: nil
    )
  }

  /// Generate a new video file URL with timestamp
  func generateVideoURL() -> URL {
    let timestamp = ISO8601DateFormatter().string(from: Date())
    let filename = "blindsighted_\(timestamp).mp4"
    return videosDirectory.appendingPathComponent(filename)
  }

  /// Get URL for a specific filename
  func videoURL(for filename: String) -> URL {
    return videosDirectory.appendingPathComponent(filename)
  }

  /// List all recorded videos
  func listVideos() throws -> [RecordedVideo] {
    let fileURLs = try FileManager.default.contentsOfDirectory(
      at: videosDirectory,
      includingPropertiesForKeys: [.creationDateKey, .fileSizeKey],
      options: [.skipsHiddenFiles]
    )

    let mp4Files = fileURLs.filter { $0.pathExtension == "mp4" }

    return try mp4Files.compactMap { url -> RecordedVideo? in
      let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
      let fileSize = attributes[.size] as? Int64 ?? 0
      let creationDate = attributes[.creationDate] as? Date ?? Date()

      // Get video duration
      let asset = AVURLAsset(url: url)
      let duration = asset.duration.seconds

      return RecordedVideo(
        id: UUID(),
        filename: url.lastPathComponent,
        recordedAt: creationDate,
        duration: duration,
        fileSize: fileSize
      )
    }.sorted { $0.recordedAt > $1.recordedAt }
  }

  /// Delete a video file
  func deleteVideo(_ video: RecordedVideo) throws {
    try FileManager.default.removeItem(at: video.url)
  }

  /// Get total size of all videos
  func totalStorageUsed() throws -> Int64 {
    let videos = try listVideos()
    return videos.reduce(0) { $0 + $1.fileSize }
  }

  /// Generate thumbnail for video
  func generateThumbnail(for video: RecordedVideo, at time: TimeInterval = 0) async -> UIImage? {
    let asset = AVURLAsset(url: video.url)
    let imageGenerator = AVAssetImageGenerator(asset: asset)
    imageGenerator.appliesPreferredTrackTransform = true

    let cmTime = CMTime(seconds: time, preferredTimescale: 600)

    do {
      let cgImage = try imageGenerator.copyCGImage(at: cmTime, actualTime: nil)
      return UIImage(cgImage: cgImage)
    } catch {
      return nil
    }
  }
}

extension TimeInterval {
  /// Format duration as MM:SS
  var formattedDuration: String {
    let minutes = Int(self) / 60
    let seconds = Int(self) % 60
    return String(format: "%02d:%02d", minutes, seconds)
  }
}

extension Int64 {
  /// Format file size as human-readable string
  var formattedFileSize: String {
    let formatter = ByteCountFormatter()
    formatter.allowedUnits = [.useKB, .useMB, .useGB]
    formatter.countStyle = .file
    return formatter.string(fromByteCount: self)
  }
}
