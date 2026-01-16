//
// LifelogView.swift
//
// Lifelog view for browsing memories from Meta wearable devices.
// Displays videos in a calendar-style grid organized by month and day.
//

import SwiftUI

// Wrapper to make (CalendarDay, Date) tuple Identifiable for sheet presentation
private struct DayWrapper: Identifiable {
  let id = UUID()
  let day: CalendarDay
  let date: Date
}

struct LifelogView: View {
  @StateObject private var viewModel: LifelogViewModel
  @State private var selectedVideo: RecordedVideo?
  @State private var selectedDayWrapper: DayWrapper?
  @Environment(\.colorScheme) var colorScheme

  init(viewModel: LifelogViewModel? = nil) {
    _viewModel = StateObject(wrappedValue: viewModel ?? LifelogViewModel())
  }

  var body: some View {
    NavigationView {
      ScrollViewReader { proxy in
        ScrollView {
          VStack(alignment: .leading, spacing: 24) {
            if viewModel.videos.isEmpty && !viewModel.isLoading {
              emptyStateView
            } else {
              ForEach(viewModel.monthSections, id: \.monthYear) { section in
                monthSection(section)
                  .id(section.monthYear)
              }
            }
          }
          .padding()
        }
        .background(Color(UIColor.systemBackground))
        .onChange(of: viewModel.monthSections) {
          if let lastSection = viewModel.monthSections.last {
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) {
              withAnimation {
                proxy.scrollTo(lastSection.monthYear, anchor: .bottom)
              }
            }
          }
        }
      }
      .navigationTitle("Memories")
      .navigationBarTitleDisplayMode(.large)
      .toolbar {
        ToolbarItem(placement: .navigationBarLeading) {
          Button(action: {
            Task {
              await viewModel.syncWithCloud()
            }
          }) {
            Label("Sync", systemImage: "arrow.triangle.2.circlepath")
          }
          .disabled(viewModel.isLoading)
          .accessibilityHint("Synchronizes your memories with cloud storage")
        }

        ToolbarItem(placement: .navigationBarTrailing) {
          Menu {
            Text("Storage: \(viewModel.totalStorage)")
            Button(role: .destructive, action: {
              // Delete all - could add confirmation dialog
            }) {
              Label("Delete All", systemImage: "trash.fill")
            }
          } label: {
            Image(systemName: "ellipsis.circle")
          }
          .accessibilityLabel("Options menu")
          .accessibilityHint("Opens storage and deletion options")
        }
      }
      .sheet(item: $selectedVideo) { video in
        VideoPlayerView(video: video)
      }
      .sheet(item: $selectedDayWrapper) { wrapper in
        LifelogDayView(day: wrapper.day, date: wrapper.date, viewModel: viewModel)
      }
      .alert("Error", isPresented: $viewModel.showError) {
        Button("OK") {
          viewModel.dismissError()
        }
      } message: {
        Text(viewModel.errorMessage)
      }
      .onAppear {
        viewModel.loadVideos()
      }
      .overlay {
        if viewModel.isLoading {
          ProgressView()
            .scaleEffect(1.5)
            .accessibilityLabel("Loading memories")
        }
      }
    }
  }

  @ViewBuilder
  private func monthSection(_ section: MonthSection) -> some View {
    VStack(alignment: .leading, spacing: 12) {
      // Month header
      Text(section.monthYear)
        .font(.title2)
        .fontWeight(.bold)
        .padding(.bottom, 4)

      // Day-of-week headers
      HStack(spacing: 0) {
        ForEach(["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"], id: \.self) { day in
          Text(day)
            .font(.caption)
            .fontWeight(.medium)
            .foregroundColor(.secondary)
            .frame(maxWidth: .infinity)
        }
      }
      .padding(.bottom, 4)

      // Calendar grid
      let weeks = section.weeks
      ForEach(0..<weeks.count, id: \.self) { weekIndex in
        HStack(spacing: 4) {
          ForEach(0..<7) { dayIndex in
            let day = weeks[weekIndex][dayIndex]
            dayCell(day: day)
          }
        }
      }
    }
  }

  @ViewBuilder
  private func dayCell(day: CalendarDay?) -> some View {
    if let day = day {
      if !day.videos.isEmpty {
        // Day with video(s)
        let firstVideo = day.videos[0]
        ZStack {
          // Thumbnail background
          if let thumbnail = viewModel.thumbnails[firstVideo.id] {
            Image(uiImage: thumbnail)
              .resizable()
              .aspectRatio(contentMode: .fill)
              .frame(width: 48, height: 48 * 16 / 9)
              .clipped()
          } else {
            RoundedRectangle(cornerRadius: 8)
              .fill(Color.gray.opacity(0.3))
              .frame(width: 48, height: 48 * 16 / 9)
          }

          // Day number overlay - centered
          Text("\(day.dayNumber)")
            .font(.system(size: 14, weight: .bold))
            .foregroundColor(.white)
            .shadow(color: .black.opacity(0.7), radius: 3)

          // Count badge in top-right corner if multiple videos
          if day.videos.count > 1 {
            VStack {
              HStack {
                Spacer()
                Text("\(day.videos.count)")
                  .font(.system(size: 10, weight: .bold))
                  .foregroundColor(.black)
                  .padding(.horizontal, 6)
                  .padding(.vertical, 3)
                  .background(Color.white)
                  .clipShape(RoundedRectangle(cornerRadius: 8))
                  .padding(4)
              }
              Spacer()
            }
          }
        }
        .frame(width: 48, height: 48 * 16 / 9)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .onTapGesture {
          handleDayTap(day: day)
        }
        .contextMenu {
          ForEach(day.videos, id: \.id) { video in
            Button {
              selectedVideo = video
            } label: {
              Label(
                formatTime(video.recordedAt),
                systemImage: "video.fill"
              )
            }
          }
          Divider()
          ForEach(day.videos, id: \.id) { video in
            Button(role: .destructive) {
              viewModel.deleteVideo(video)
            } label: {
              Label("Delete \(formatTime(video.recordedAt))", systemImage: "trash")
            }
          }
        }
      } else {
        // Day without video
        Text("\(day.dayNumber)")
          .font(.system(size: 14))
          .foregroundColor(.secondary)
          .frame(minWidth: 48, minHeight: 48 * 16 / 9)
      }
    } else {
      // Empty cell (padding days from other months)
      Color.clear
        .frame(minWidth: 48, minHeight: 48 * 16 / 9)
    }
  }

  private func formatTime(_ date: Date) -> String {
    let formatter = DateFormatter()
    formatter.timeStyle = .short
    return formatter.string(from: date)
  }

  private func handleDayTap(day: CalendarDay) {
    if day.videos.count > 1 {
      // Multiple videos: show day view
      // Calculate the date for this day
      if let section = viewModel.monthSections.first(where: { section in
        section.weeks.contains(where: { week in
          week.contains(where: { $0?.dayNumber == day.dayNumber })
        })
      }) {
        // Parse the month/year and combine with day number
        let formatter = DateFormatter()
        formatter.dateFormat = "MMMM yyyy"
        if let monthDate = formatter.date(from: section.monthYear) {
          let calendar = Calendar.current
          var components = calendar.dateComponents([.year, .month], from: monthDate)
          components.day = day.dayNumber
          if let dayDate = calendar.date(from: components) {
            selectedDayWrapper = DayWrapper(day: day, date: dayDate)
          }
        }
      }
    } else if let video = day.videos.first {
      // Single video: show video player directly
      selectedVideo = video
    }
  }

  private var emptyStateView: some View {
    VStack(spacing: 16) {
      Image(systemName: "video.slash")
        .font(.system(size: 60))
        .foregroundColor(.secondary)

      Text("No Memories")
        .font(.title2)
        .fontWeight(.semibold)

      Text("Start recording to save memories from your glasses")
        .font(.subheadline)
        .foregroundColor(.secondary)
        .multilineTextAlignment(.center)
        .padding(.horizontal, 40)
    }
    .frame(maxWidth: .infinity, maxHeight: .infinity)
    .padding(.top, 100)
  }
}


#if DEBUG
#Preview("Empty State") {
  LifelogView()
}

#Preview("With Memories - January 2025") {
  // Preview showing calendar layout with videos from PreviewContent directory
  LifelogView(viewModel: LifelogViewModel(fileManager: PreviewVideoFileManager.shared))
}
#endif
