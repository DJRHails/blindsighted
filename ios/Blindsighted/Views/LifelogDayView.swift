//
// LifelogDayView.swift
//
// Detailed day view showing all videos from a single day with timeline visualization.
// Videos are sized proportionally to their duration, with gaps representing time between recordings.
//

import SwiftUI

struct LifelogDayView: View {
  let day: CalendarDay
  let date: Date
  @StateObject private var viewModel: LifelogViewModel
  @State private var selectedVideo: RecordedVideo?
  @Environment(\.dismiss) var dismiss

  init(day: CalendarDay, date: Date, viewModel: LifelogViewModel) {
    self.day = day
    self.date = date
    _viewModel = StateObject(wrappedValue: viewModel)
  }

  var body: some View {
    NavigationView {
      ScrollView {
        VStack(alignment: .leading, spacing: 24) {
          // Header with humanized date
          dateHeader

          // Timeline of videos
          if !day.videos.isEmpty {
            timelineView
          }
        }
        .padding()
      }
      .background(Color(UIColor.systemBackground))
      .navigationBarTitleDisplayMode(.inline)
      .toolbar {
        ToolbarItem(placement: .navigationBarLeading) {
          Button("Done") {
            dismiss()
          }
        }
      }
      .sheet(item: $selectedVideo) { video in
        VideoPlayerView(video: video)
      }
    }
  }

  private var dateHeader: some View {
    HStack(alignment: .firstTextBaseline, spacing: 12) {
      Text(humanizedDate)
        .font(.largeTitle)
        .fontWeight(.bold)

      Text(formattedDate)
        .font(.title2)
        .foregroundColor(.secondary)
    }
  }

  private var timelineView: some View {
    VStack(spacing: 16) {
      let sortedVideos = day.videos.sorted { $0.recordedAt < $1.recordedAt }

      ForEach(Array(sortedVideos.enumerated()), id: \.element.id) { index, video in
        // Video cell
        videoCell(video: video)

        // Show gap after this video (except for last video)
        // Only show gap if it's 15 minutes or more
        if index < sortedVideos.count - 1 {
          let nextVideo = sortedVideos[index + 1]
          let gapDuration = nextVideo.recordedAt.timeIntervalSince(
            video.recordedAt.addingTimeInterval(video.duration)
          )

          if gapDuration >= 900 { // 15 minutes = 900 seconds
            gapView(
              from: video.recordedAt.addingTimeInterval(video.duration),
              to: nextVideo.recordedAt
            )
          }
        }
      }
    }
  }

  private func videoCell(video: RecordedVideo) -> some View {
    let cellHeight = max(100, CGFloat(video.duration) * 2)

    return Button {
      selectedVideo = video
    } label: {
      ZStack {
        // Thumbnail background - fills entire cell
        if let thumbnail = viewModel.thumbnails[video.id] {
          Image(uiImage: thumbnail)
            .resizable()
            .aspectRatio(contentMode: .fill)
            .frame(height: cellHeight)
            .clipped()
        } else {
          Color.gray.opacity(0.3)
        }

        // Dark gradient overlay for better text readability
        LinearGradient(
          gradient: Gradient(colors: [
            Color.black.opacity(0.6),
            Color.black.opacity(0.3),
            Color.clear,
            Color.black.opacity(0.3),
            Color.black.opacity(0.6)
          ]),
          startPoint: .leading,
          endPoint: .trailing
        )

        // Content overlay
        HStack(spacing: 16) {
          VStack(alignment: .leading, spacing: 4) {
            Text(formatTime(video.recordedAt))
              .font(.headline)
              .foregroundColor(.white)
              .shadow(color: .black.opacity(0.5), radius: 2)

            Text(formatDuration(video.duration))
              .font(.subheadline)
              .foregroundColor(.white.opacity(0.9))
              .shadow(color: .black.opacity(0.5), radius: 2)

            if let locationDesc = video.locationDescription {
              HStack(spacing: 4) {
                Image(systemName: "location.fill")
                  .font(.caption)
                Text(locationDesc)
                  .font(.caption)
              }
              .foregroundColor(.white.opacity(0.8))
              .shadow(color: .black.opacity(0.5), radius: 2)
            }
          }

          Spacer()

          Image(systemName: "chevron.right")
            .foregroundColor(.white.opacity(0.8))
            .font(.caption)
            .shadow(color: .black.opacity(0.5), radius: 2)
        }
        .padding()
      }
      .frame(height: cellHeight)
      .clipShape(RoundedRectangle(cornerRadius: 12))
    }
    .buttonStyle(.plain)
    .contextMenu {
      Button(role: .destructive) {
        viewModel.deleteVideo(video)
        if day.videos.count <= 1 {
          dismiss()
        }
      } label: {
        Label("Delete", systemImage: "trash")
      }
    }
  }

  private func gapView(from: Date, to: Date) -> some View {
    let gap = to.timeIntervalSince(from)
    // Scale gap height: 50pt at 15min, uncapped for longer durations
    // Formula: 50 + (gap_seconds * 0.04)
    let gapHeight = 50 + CGFloat(gap) * 0.04
    let hours = Int(gap) / 3600

    return VStack(spacing: 0) {
      Divider()

      ZStack {
        // Background: Hour dividing lines
        if hours > 0 {
          VStack(spacing: 0) {
            let hourHeight = gapHeight / CGFloat(hours)

            ForEach(0..<hours, id: \.self) { _ in
              Spacer()
                .frame(height: hourHeight)

              HStack {
                Spacer()
                Rectangle()
                  .fill(Color.secondary.opacity(0.3))
                  .frame(width: 40, height: 1)
                Spacer()
              }
            }

            Spacer()
              .frame(height: hourHeight)
          }
        }

        // Foreground: Centered time label
        VStack(spacing: 2) {
          Image(systemName: "clock")
            .font(.system(size: 10))
            .foregroundColor(.secondary)

          Text(formatGap(gap))
            .font(.system(size: 10))
            .foregroundColor(.secondary)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
        .background(Color(UIColor.systemBackground))
        .cornerRadius(8)
      }
      .frame(height: gapHeight)

      Divider()
    }
  }

  // MARK: - Date Formatting

  private var humanizedDate: String {
    let calendar = Calendar.current

    if calendar.isDateInToday(date) {
      return "Today"
    } else if calendar.isDateInYesterday(date) {
      return "Yesterday"
    } else if let daysAgo = calendar.dateComponents([.day], from: date, to: Date()).day,
              daysAgo >= 0 && daysAgo < 7 {
      // Last week: "Last Tuesday"
      let weekday = date.formatted(.dateTime.weekday(.wide))
      return "Last \(weekday)"
    } else if let weeksAgo = calendar.dateComponents([.weekOfYear], from: date, to: Date()).weekOfYear,
              weeksAgo == 1 {
      // Last week but more than 7 days ago
      let weekday = date.formatted(.dateTime.weekday(.wide))
      return "Last \(weekday)"
    } else {
      // Older dates: show full month day
      return date.formatted(.dateTime.month(.wide).day())
    }
  }

  private var formattedDate: String {
    date.formatted(.dateTime.day().month(.wide))
  }

  private func formatTime(_ date: Date) -> String {
    date.formatted(.dateTime.hour().minute())
  }

  private func formatDuration(_ duration: TimeInterval) -> String {
    let minutes = Int(duration) / 60
    let seconds = Int(duration) % 60

    if minutes > 0 {
      return String(format: "%d:%02d", minutes, seconds)
    } else {
      return String(format: "%ds", seconds)
    }
  }

  private func formatGap(_ gap: TimeInterval) -> String {
    let hours = Int(gap) / 3600
    let minutes = (Int(gap) % 3600) / 60

    if hours > 0 {
      return String(format: "%dh %dm", hours, minutes)
    } else if minutes > 0 {
      return String(format: "%dm", minutes)
    } else {
      return "< 1m"
    }
  }
}

#if DEBUG
#Preview("Day View") {
  // Create sample videos for preview
  let baseDate = Date()
  let videos = [
    RecordedVideo(
      id: UUID(),
      filename: "video1.mp4",
      recordedAt: baseDate.addingTimeInterval(-7200), // 2 hours ago
      duration: 45,
      fileSize: 1024 * 1024 * 10,
      metadata: nil
    ),
    RecordedVideo(
      id: UUID(),
      filename: "video2.mp4",
      recordedAt: baseDate.addingTimeInterval(-3600), // 1 hour ago
      duration: 120,
      fileSize: 1024 * 1024 * 20,
      metadata: nil
    ),
    RecordedVideo(
      id: UUID(),
      filename: "video3.mp4",
      recordedAt: baseDate.addingTimeInterval(-1800), // 30 min ago
      duration: 30,
      fileSize: 1024 * 1024 * 5,
      metadata: nil
    )
  ]

  let day = CalendarDay(dayNumber: 16, videos: videos)

  LifelogDayView(
    day: day,
    date: baseDate,
    viewModel: LifelogViewModel()
  )
}
#endif
