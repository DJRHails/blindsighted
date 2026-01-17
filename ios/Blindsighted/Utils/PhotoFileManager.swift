//
// PhotoFileManager.swift
//
// Manages photo file storage and retrieval in the app's Documents directory.
// Handles periodic photo capture storage during recording sessions.
//

import Foundation
import UIKit

let PHOTOS_DIRECTORY = "BlindsightedPhotos"

struct CapturedPhoto: Identifiable, Codable {
  let id: UUID
  let filename: String
  let capturedAt: Date
  let fileSize: Int64

  var url: URL {
    PhotoFileManager.shared.photoURL(for: filename)
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
  @discardableResult
  func savePhoto(_ image: UIImage, quality: CGFloat = 0.8) -> URL? {
    guard let data = image.jpegData(compressionQuality: quality) else {
      return nil
    }

    let timestamp = ISO8601DateFormatter().string(from: Date())
      .replacingOccurrences(of: ":", with: "-")  // Remove colons for filename compatibility
    let filename = "photo_\(timestamp).jpg"
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
  func listPhotos() throws -> [CapturedPhoto] {
    let fileURLs = try FileManager.default.contentsOfDirectory(
      at: photosDirectory,
      includingPropertiesForKeys: [.creationDateKey, .fileSizeKey],
      options: [.skipsHiddenFiles]
    )

    let jpgFiles = fileURLs.filter { $0.pathExtension.lowercased() == "jpg" }

    return try jpgFiles.compactMap { url -> CapturedPhoto? in
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
