//
// PreviewVideoSeeder.swift
//
// Seeds the app with preview videos from R2 in development mode.
// Only runs once on first launch to populate the Lifelog with sample data.
//

import Foundation
import AVFoundation

struct PreviewVideoInfo: Codable {
    let filename: String
    let videoUrl: String
    let metadata: VideoMetadata

    enum CodingKeys: String, CodingKey {
        case filename
        case videoUrl = "video_url"
        case metadata
    }
}

struct PreviewVideosResponse: Codable {
    let videos: [PreviewVideoInfo]
}

class PreviewVideoSeeder {
    static let shared = PreviewVideoSeeder()

    private let userDefaultsKey = "PreviewVideosSeeded"
    private let apiBaseURL: String

    private init() {
        // Get API base URL from Info.plist
        if let url = Bundle.main.object(forInfoDictionaryKey: "API_BASE_URL") as? String {
            self.apiBaseURL = url
        } else {
            self.apiBaseURL = "http://localhost:8000"
        }
    }

    /// Check if preview videos have already been seeded
    var hasSeededVideos: Bool {
        UserDefaults.standard.bool(forKey: userDefaultsKey)
    }

    /// Seed preview videos from R2 into the app's video directory
    func seedVideosIfNeeded() async {
        #if DEBUG
        // Only run in debug/development mode
        guard !hasSeededVideos else {
            print("Preview videos already seeded, skipping")
            return
        }

        do {
            print("Starting preview video seeding...")
            try await seedVideos()
            UserDefaults.standard.set(true, forKey: userDefaultsKey)
            print("Successfully seeded preview videos")
        } catch {
            print("Failed to seed preview videos: \(error)")
        }
        #endif
    }

    /// Force re-seed videos (useful for testing)
    func resetAndReseed() async throws {
        UserDefaults.standard.set(false, forKey: userDefaultsKey)
        try await seedVideos()
        UserDefaults.standard.set(true, forKey: userDefaultsKey)
    }

    private func seedVideos() async throws {
        // Fetch list of preview videos from API
        let videosURL = URL(string: "\(apiBaseURL)/preview/videos")!
        let (data, _) = try await URLSession.shared.data(from: videosURL)
        let response = try JSONDecoder().decode(PreviewVideosResponse.self, from: data)

        print("Found \(response.videos.count) preview videos to download")

        // Download each video and its metadata
        for videoInfo in response.videos {
            try await downloadVideo(videoInfo)
        }
    }

    private func downloadVideo(_ videoInfo: PreviewVideoInfo) async throws {
        print("Downloading \(videoInfo.filename)...")

        // Download video file
        guard let videoURL = URL(string: videoInfo.videoUrl) else {
            throw URLError(.badURL)
        }

        let (videoData, _) = try await URLSession.shared.data(from: videoURL)

        // Save video to app's video directory
        let destinationURL = VideoFileManager.shared.videoURL(for: videoInfo.filename)
        try videoData.write(to: destinationURL)
        print("  ✓ Saved video to \(destinationURL.lastPathComponent)")

        // Save metadata (already included in API response)
        try VideoFileManager.shared.saveMetadata(videoInfo.metadata, for: videoInfo.filename)
        print("  ✓ Saved metadata")
    }
}
