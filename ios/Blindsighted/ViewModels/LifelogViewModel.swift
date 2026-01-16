//
// LifelogViewModel.swift
//
// View model for managing the lifelog/memories view, organizing videos by calendar date.
//

import Foundation
import SwiftUI

// Calendar data structures
struct MonthSection: Equatable {
  let monthYear: String
  let weeks: [[CalendarDay?]]

  static func == (lhs: MonthSection, rhs: MonthSection) -> Bool {
    lhs.monthYear == rhs.monthYear
  }
}

struct CalendarDay: Equatable {
  let dayNumber: Int
  let videos: [RecordedVideo]

  static func == (lhs: CalendarDay, rhs: CalendarDay) -> Bool {
    lhs.dayNumber == rhs.dayNumber && lhs.videos.map(\.id) == rhs.videos.map(\.id)
  }
}

@MainActor
class LifelogViewModel: ObservableObject {
  @Published var videos: [RecordedVideo] = []
  @Published var thumbnails: [UUID: UIImage] = [:]
  @Published var monthSections: [MonthSection] = []
  @Published var isLoading: Bool = false
  @Published var showError: Bool = false
  @Published var errorMessage: String = ""
  @Published var totalStorage: String = "0 MB"

  private let fileManager: VideoFileManagerProtocol
  private let syncManager = LifelogSyncManager.shared
  private let calendar = Calendar.current

  init(fileManager: VideoFileManagerProtocol = VideoFileManager.shared) {
    self.fileManager = fileManager
    loadVideos()
  }

  func syncWithCloud() async {
    isLoading = true
    await syncManager.sync()
    loadVideos()
  }

  func loadVideos() {
    isLoading = true

    Task {
      do {
        videos = try fileManager.listVideos()
        try updateTotalStorage()
        organizeIntoCalendar()

        // Generate thumbnails for visible videos
        for video in videos.prefix(50) {
          await generateThumbnail(for: video)
        }

        isLoading = false
      } catch {
        showError("Failed to load videos: \(error.localizedDescription)")
        isLoading = false
      }
    }
  }

  private func organizeIntoCalendar() {
    // Group videos by month
    var videosByMonth: [String: [RecordedVideo]] = [:]

    for video in videos {
      let monthYear = formatMonthYear(video.recordedAt)
      if videosByMonth[monthYear] == nil {
        videosByMonth[monthYear] = []
      }
      videosByMonth[monthYear]?.append(video)
    }

    // Create month sections with calendar grid (oldest first, latest at bottom)
    monthSections = videosByMonth.keys.sorted(by: <).map { monthYear in
      createMonthSection(monthYear: monthYear, videos: videosByMonth[monthYear] ?? [])
    }
  }

  private func createMonthSection(monthYear: String, videos: [RecordedVideo]) -> MonthSection {
    // Parse month and year
    let formatter = DateFormatter()
    formatter.dateFormat = "MMMM yyyy"
    guard let date = formatter.date(from: monthYear) else {
      return MonthSection(monthYear: monthYear, weeks: [])
    }

    // Get first day of month and number of days
    let components = calendar.dateComponents([.year, .month], from: date)
    guard let firstDayOfMonth = calendar.date(from: components),
      let range = calendar.range(of: .day, in: .month, for: firstDayOfMonth)
    else {
      return MonthSection(monthYear: monthYear, weeks: [])
    }

    let numberOfDays = range.count

    // Get weekday of first day (1 = Sunday, 2 = Monday, etc.)
    let firstWeekday = calendar.component(.weekday, from: firstDayOfMonth)
    // Convert to Monday-based (0 = Monday, 6 = Sunday)
    let mondayBasedOffset = (firstWeekday == 1) ? 6 : (firstWeekday - 2)

    // Create video lookup by day (support multiple videos per day)
    var videosByDay: [Int: [RecordedVideo]] = [:]
    for video in videos {
      let day = calendar.component(.day, from: video.recordedAt)
      if videosByDay[day] == nil {
        videosByDay[day] = []
      }
      videosByDay[day]?.append(video)
    }

    // Build calendar grid
    var weeks: [[CalendarDay?]] = []
    var currentWeek: [CalendarDay?] = []

    // Add padding for days before first day of month
    for _ in 0..<mondayBasedOffset {
      currentWeek.append(nil)
    }

    // Get current date for filtering future dates
    let today = Date()

    // Add days of month
    for day in 1...numberOfDays {
      // Create date for this day to check if it's in the future
      var dayComponents = components
      dayComponents.day = day
      guard let dayDate = calendar.date(from: dayComponents) else { continue }

      // Only show dates up to today
      if dayDate <= today {
        let calendarDay = CalendarDay(dayNumber: day, videos: videosByDay[day] ?? [])
        currentWeek.append(calendarDay)
      } else {
        // Add nil for future dates
        currentWeek.append(nil)
      }

      if currentWeek.count == 7 {
        weeks.append(currentWeek)
        currentWeek = []
      }
    }

    // Add padding for remaining days in last week
    if !currentWeek.isEmpty {
      while currentWeek.count < 7 {
        currentWeek.append(nil)
      }
      weeks.append(currentWeek)
    }

    return MonthSection(monthYear: monthYear, weeks: weeks)
  }

  private func formatMonthYear(_ date: Date) -> String {
    let formatter = DateFormatter()
    formatter.dateFormat = "MMMM yyyy"
    return formatter.string(from: date)
  }

  func generateThumbnail(for video: RecordedVideo) async {
    guard thumbnails[video.id] == nil else { return }

      if let thumbnail = await fileManager.generateThumbnail(for: video, at: video.duration / 2) {
      thumbnails[video.id] = thumbnail
    }
  }

  func deleteVideo(_ video: RecordedVideo) {
    do {
      try fileManager.deleteVideo(video)
      videos.removeAll { $0.id == video.id }
      thumbnails.removeValue(forKey: video.id)
      organizeIntoCalendar()
      try? updateTotalStorage()
    } catch {
      showError("Failed to delete video: \(error.localizedDescription)")
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
