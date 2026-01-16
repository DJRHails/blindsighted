//
// PreviewVideoFileManager.swift
//
// Mock video file manager for SwiftUI previews that loads videos from PreviewContent directory.
//

import AVFoundation
import CoreLocation
import Foundation
import SwiftUI

#if DEBUG
class PreviewVideoFileManager: VideoFileManagerProtocol {
    func deleteVideo(_ video: RecordedVideo) throws {
        throw NSError(domain: "PreviewVideoFileManager", code: 0, userInfo: [NSLocalizedDescriptionKey: "Deleting videos is not supported in preview mode"])
    }

  static let shared = PreviewVideoFileManager()

  private let videosDirectory: URL

  /// Mapping of video filenames to their timestamps for preview purposes
  private static let videoTimestamps: [String: String] = [
    "monkey_jungle.mp4": "2025-12-15T18:30:00Z",
    "market_bazaar.mp4": "2026-01-02T14:30:00Z",
    "proposal.mp4": "2026-01-02T16:20:00Z",
    "park_walk.mp4": "2026-01-03T10:15:00Z",
    "workspace_overhead.mp4": "2026-01-08T16:45:00Z",
    "lanterns.mp4": "2026-01-09T12:20:00Z",
    "city_street_philadelphia.mp4": "2026-01-10T09:30:00Z",
    "city_aerial_sunset.mp4": "2026-01-11T15:10:00Z",
    "boat_seagulls.mp4": "2026-01-12T11:40:00Z",
    "underwater_manta_rays.mp4": "2026-01-13T10:25:00Z",
    "scuba_diving_fish_school.mp4": "2026-01-13T13:50:00Z",
    "sea_turtle_dive.mp4": "2026-01-13T15:05:00Z",
    "desert_sunset.mp4": "2026-01-15T18:15:00Z",
    "monkey_jungle_2.mp4": "2026-01-15T12:30:00Z"
  ]

  private init() {
    // Get the project's PreviewContent/Videos directory
    let projectPath = URL(fileURLWithPath: #file)
      .deletingLastPathComponent()  // Remove PreviewVideoFileManager.swift
      .deletingLastPathComponent()  // Remove Utils
      .deletingLastPathComponent()  // Remove Blindsighted
      .appendingPathComponent("PreviewContent")
      .appendingPathComponent("Videos")

    self.videosDirectory = projectPath
  }

  /// List all recorded videos from preview directory
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

      let filename = url.lastPathComponent

      // Get timestamp from mapping, fallback to current date if not found
      let isoFormatter = ISO8601DateFormatter()
      let recordedDate: Date
      if let timestampString = Self.videoTimestamps[filename] {
        recordedDate = isoFormatter.date(from: timestampString) ?? Date()
      } else {
        recordedDate = Date()
      }

      // Get video duration
      let asset = AVURLAsset(url: url)
      let duration = asset.duration.seconds

      return RecordedVideo(
        id: UUID(),
        filename: url.lastPathComponent,
        recordedAt: recordedDate,
        duration: duration,
        fileSize: fileSize,
        metadata: nil
      )
    }.sorted { $0.recordedAt > $1.recordedAt }
  }

  /// Get URL for a specific filename
  func videoURL(for filename: String) -> URL {
    return videosDirectory.appendingPathComponent(filename)
  }

  /// Generate thumbnail for video
  func generateThumbnail(for video: RecordedVideo, at time: TimeInterval = 0) async -> UIImage? {
    let url = videoURL(for: video.filename)
    let asset = AVURLAsset(url: url)
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

  /// Get total size of all videos
  func totalStorageUsed() throws -> Int64 {
    let videos = try listVideos()
    return videos.reduce(0) { $0 + $1.fileSize }
  }
}
#endif
