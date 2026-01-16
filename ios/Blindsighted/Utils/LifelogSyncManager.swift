//
// LifelogSyncManager.swift
//
// Manages synchronization of lifelog videos between local device and cloud storage.
// Uses SHA256 hashing to detect changes and avoid re-uploading identical videos.
//

import Foundation
import CryptoKit
import UIKit

// MARK: - API Response Models

struct LifelogEntryDTO: Codable {
    let id: String
    let filename: String
    let videoHash: String
    let r2Url: String
    let recordedAt: Date
    let durationSeconds: Double
    let fileSizeBytes: Int
    let latitude: Double?
    let longitude: Double?
    let altitude: Double?
    let heading: Double?
    let speed: Double?
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id, filename
        case videoHash = "video_hash"
        case r2Url = "r2_url"
        case recordedAt = "recorded_at"
        case durationSeconds = "duration_seconds"
        case fileSizeBytes = "file_size_bytes"
        case latitude, longitude, altitude, heading, speed
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct SyncResponse: Codable {
    let entries: [LifelogEntryDTO]
    let totalCount: Int
    let lastSyncAt: Date

    enum CodingKeys: String, CodingKey {
        case entries
        case totalCount = "total_count"
        case lastSyncAt = "last_sync_at"
    }
}

struct UploadResponse: Codable {
    let id: String
    let videoHash: String
    let r2Url: String
    let alreadyExists: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case videoHash = "video_hash"
        case r2Url = "r2_url"
        case alreadyExists = "already_exists"
    }
}

// MARK: - Sync Manager

@MainActor
class LifelogSyncManager: ObservableObject {
    static let shared = LifelogSyncManager()

    @Published var isSyncing = false
    @Published var lastSyncDate: Date?
    @Published var syncError: String?

    private let apiBaseURL: String
    private let deviceIdentifier: String

    private init() {
        // Get API base URL from Info.plist
        if let apiConfig = Bundle.main.object(forInfoDictionaryKey: "APIConfig") as? [String: String],
           let url = apiConfig["BaseURL"] {
            self.apiBaseURL = url
        } else {
            self.apiBaseURL = "https://api.blindsighted.hails.info"
        }

        // Get device identifier (use iOS device UUID)
        self.deviceIdentifier = UIDevice.current.identifierForVendor?.uuidString ?? "unknown-device"
    }

    /// Perform full sync: download cloud entries and upload local entries
    func sync() async {
        guard !isSyncing else { return }

        isSyncing = true
        syncError = nil
        defer { isSyncing = false }

        do {
            print("[Sync] Starting lifelog sync for device: \(deviceIdentifier)")

            // Step 1: Get cloud entries
            let cloudEntries = try await fetchCloudEntries()
            print("[Sync] Found \(cloudEntries.count) entries in cloud")

            // Step 2: Get local videos
            let localVideos = try VideoFileManager.shared.listVideos()
            print("[Sync] Found \(localVideos.count) local videos")

            // Step 3: Calculate local hashes
            let localHashes = try await calculateLocalHashes(for: localVideos)

            // Step 4: Download missing videos from cloud
            try await downloadMissingVideos(cloudEntries: cloudEntries, localHashes: localHashes)

            // Step 5: Upload new local videos to cloud
            try await uploadNewVideos(localVideos: localVideos, cloudHashes: Set(cloudEntries.map(\.videoHash)))

            lastSyncDate = Date()
            print("[Sync] Sync completed successfully")

        } catch {
            syncError = error.localizedDescription
            print("[Sync] Sync failed: \(error)")
        }
    }

    // MARK: - Private Methods

    private func fetchCloudEntries() async throws -> [LifelogEntryDTO] {
        let url = URL(string: "\(apiBaseURL)/lifelog/sync/\(deviceIdentifier)")!
        let (data, _) = try await URLSession.shared.data(from: url)

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601
        let response = try decoder.decode(SyncResponse.self, from: data)

        return response.entries
    }

    private func calculateLocalHashes(for videos: [RecordedVideo]) async throws -> [String: RecordedVideo] {
        var hashMap: [String: RecordedVideo] = [:]

        for video in videos {
            let hash = try await calculateSHA256(for: video.url)
            hashMap[hash] = video
        }

        return hashMap
    }

    private func calculateSHA256(for url: URL) async throws -> String {
        return try await Task.detached {
            let data = try Data(contentsOf: url)
            let hash = SHA256.hash(data: data)
            return hash.compactMap { String(format: "%02x", $0) }.joined()
        }.value
    }

    private func downloadMissingVideos(
        cloudEntries: [LifelogEntryDTO],
        localHashes: [String: RecordedVideo]
    ) async throws {
        for entry in cloudEntries {
            // Skip if we already have this video locally
            if localHashes[entry.videoHash] != nil {
                continue
            }

            print("[Sync] Downloading missing video: \(entry.filename)")

            // Download video from R2
            guard let videoURL = URL(string: entry.r2Url) else {
                print("[Sync] Invalid video URL: \(entry.r2Url)")
                continue
            }

            let (videoData, _) = try await URLSession.shared.data(from: videoURL)

            // Save to local storage
            let destinationURL = VideoFileManager.shared.videoURL(for: entry.filename)
            try videoData.write(to: destinationURL)

            // Save metadata
            let metadata = VideoMetadata(
                latitude: entry.latitude,
                longitude: entry.longitude,
                altitude: entry.altitude,
                heading: entry.heading,
                speed: entry.speed,
                timestamp: entry.recordedAt
            )
            try VideoFileManager.shared.saveMetadata(metadata, for: entry.filename)

            print("[Sync] Downloaded: \(entry.filename)")
        }
    }

    private func uploadNewVideos(
        localVideos: [RecordedVideo],
        cloudHashes: Set<String>
    ) async throws {
        for video in localVideos {
            // Calculate hash for this video
            let hash = try await calculateSHA256(for: video.url)

            // Skip if cloud already has this video
            if cloudHashes.contains(hash) {
                continue
            }

            print("[Sync] Uploading new video: \(video.filename)")
            try await uploadVideo(video, hash: hash)
        }
    }

    private func uploadVideo(_ video: RecordedVideo, hash: String) async throws {
        let url = URL(string: "\(apiBaseURL)/lifelog/upload/\(deviceIdentifier)")!

        // Read video data
        let videoData = try Data(contentsOf: video.url)

        // Create multipart form data
        var request = URLRequest(url: url)
        request.httpMethod = "POST"

        let boundary = UUID().uuidString
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        var body = Data()

        // Add video file
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"video\"; filename=\"\(video.filename)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: video/mp4\r\n\r\n".data(using: .utf8)!)
        body.append(videoData)
        body.append("\r\n".data(using: .utf8)!)

        // Add form fields
        addFormField(to: &body, boundary: boundary, name: "filename", value: video.filename)
        addFormField(to: &body, boundary: boundary, name: "recorded_at", value: ISO8601DateFormatter().string(from: video.recordedAt))
        addFormField(to: &body, boundary: boundary, name: "duration_seconds", value: String(video.duration))

        // Add optional location metadata
        if let lat = video.metadata?.latitude {
            addFormField(to: &body, boundary: boundary, name: "latitude", value: String(lat))
        }
        if let lon = video.metadata?.longitude {
            addFormField(to: &body, boundary: boundary, name: "longitude", value: String(lon))
        }
        if let alt = video.metadata?.altitude {
            addFormField(to: &body, boundary: boundary, name: "altitude", value: String(alt))
        }
        if let heading = video.metadata?.heading {
            addFormField(to: &body, boundary: boundary, name: "heading", value: String(heading))
        }
        if let speed = video.metadata?.speed {
            addFormField(to: &body, boundary: boundary, name: "speed", value: String(speed))
        }

        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        // Send request
        let (responseData, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let uploadResponse = try decoder.decode(UploadResponse.self, from: responseData)

        print("[Sync] Uploaded: \(video.filename) (hash: \(uploadResponse.videoHash))")
    }

    private func addFormField(to body: inout Data, boundary: String, name: String, value: String) {
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"\(name)\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(value)\r\n".data(using: .utf8)!)
    }
}

// MARK: - VideoMetadata Extension

extension VideoMetadata {
    init(latitude: Double?, longitude: Double?, altitude: Double?, heading: Double?, speed: Double?, timestamp: Date) {
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.heading = heading
        self.speed = speed
        self.timestamp = timestamp
    }
}
