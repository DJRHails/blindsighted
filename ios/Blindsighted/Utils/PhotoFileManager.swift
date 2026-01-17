//
// PhotoFileManager.swift
//
// Manages photo file storage and retrieval in the app's Documents directory.
// Handles periodic photo capture storage during recording sessions.
//

import Foundation
import UIKit

let PHOTOS_DIRECTORY = "BlindsightedPhotos"

/// Flag indicating the type of photo analysis needed
enum PhotoFlag: String, Codable {
  case low = "low"    // Navigation mode - guide user positioning
  case high = "high"  // Identification mode - list shelf items
}

struct CapturedPhoto: Identifiable, Codable {
  let id: UUID
  let filename: String
  let capturedAt: Date
  let fileSize: Int64

  var url: URL {
    PhotoFileManager.shared.photoURL(for: filename)
  }

  /// Parse flag from filename (e.g., "photo_2026-01-17_low.jpg" -> .low)
  var flag: PhotoFlag? {
    if filename.contains("_low.") { return .low }
    if filename.contains("_high.") { return .high }
    return nil
  }
}

class PhotoFileManager {
  static let shared = PhotoFileManager()

  private let photosDirectory: URL

  private init() {
    let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
    self.photosDirectory = documentsPath.appendingPathComponent(PHOTOS_DIRECTORY, isDirectory: true)

    // Create photos directory if it doesn't exist
    try? FileManager.default.createDirectory(
      at: photosDirectory,
      withIntermediateDirectories: true,
      attributes: nil
    )
  }

  /// Get the photos directory URL (for Files app access info)
  var directoryURL: URL {
    photosDirectory
  }

  /// Save a photo and return its URL
  /// - Parameters:
  ///   - image: The UIImage to save
  ///   - flag: Optional PhotoFlag to embed in filename (low/high)
  ///   - quality: JPEG compression quality (0.0 to 1.0)
  /// - Returns: URL of saved photo, or nil if save failed
  @discardableResult
  func savePhoto(_ image: UIImage, flag: PhotoFlag? = nil, quality: CGFloat = 0.8) -> URL? {
    guard let data = image.jpegData(compressionQuality: quality) else {
      return nil
    }

    let timestamp = ISO8601DateFormatter().string(from: Date())
      .replacingOccurrences(of: ":", with: "-")  // Remove colons for filename compatibility
    let flagSuffix = flag.map { "_\($0.rawValue)" } ?? ""
    let filename = "photo_\(timestamp)\(flagSuffix).jpg"
    let url = photosDirectory.appendingPathComponent(filename)

    do {
      try data.write(to: url)
      return url
    } catch {
      print("Failed to save photo: \(error)")
      return nil
    }
  }

  /// Get URL for a specific filename
  func photoURL(for filename: String) -> URL {
    return photosDirectory.appendingPathComponent(filename)
  }

  /// List all captured photos
  /// - Parameter flag: Optional flag to filter by (nil returns all photos)
  /// - Returns: Array of CapturedPhoto sorted by date (most recent first)
  func listPhotos(withFlag flag: PhotoFlag? = nil) throws -> [CapturedPhoto] {
    let fileURLs = try FileManager.default.contentsOfDirectory(
      at: photosDirectory,
      includingPropertiesForKeys: [.creationDateKey, .fileSizeKey],
      options: [.skipsHiddenFiles]
    )

    let jpgFiles = fileURLs.filter { $0.pathExtension.lowercased() == "jpg" }

    let photos = try jpgFiles.compactMap { url -> CapturedPhoto? in
      let attributes = try FileManager.default.attributesOfItem(atPath: url.path)
      let fileSize = attributes[.size] as? Int64 ?? 0
      let creationDate = attributes[.creationDate] as? Date ?? Date()

      return CapturedPhoto(
        id: UUID(),
        filename: url.lastPathComponent,
        capturedAt: creationDate,
        fileSize: fileSize
      )
    }.sorted { $0.capturedAt > $1.capturedAt }  // Most recent first

    // Filter by flag if specified
    if let flag = flag {
      return photos.filter { $0.flag == flag }
    }
    return photos
  }

  /// Delete a single photo
  func deletePhoto(_ photo: CapturedPhoto) throws {
    try FileManager.default.removeItem(at: photo.url)
  }

  /// Delete all photos
  func deleteAllPhotos() throws {
    let photos = try listPhotos()
    for photo in photos {
      try? FileManager.default.removeItem(at: photo.url)
    }
  }

  /// Get total storage used by photos
  func totalStorageUsed() throws -> Int64 {
    let photos = try listPhotos()
    return photos.reduce(0) { $0 + $1.fileSize }
  }

  /// Get photo count
  func photoCount() -> Int {
    return (try? listPhotos().count) ?? 0
  }

  /// Load image from a captured photo
  func loadImage(for photo: CapturedPhoto) -> UIImage? {
    return UIImage(contentsOfFile: photo.url.path)
  }
}
