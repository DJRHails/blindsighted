//
// MainAppView.swift
//
// Central navigation hub that displays different views based on DAT SDK registration and device states.
// When unregistered, shows the registration flow. When registered, shows the device selection screen
// for choosing which Meta wearable device to stream from.
//

import MWDATCore
import SwiftUI

struct MainAppView: View {
  let wearables: WearablesInterface
  @ObservedObject private var viewModel: WearablesViewModel
  @State private var selectedTab: Int = 0

  init(wearables: WearablesInterface, viewModel: WearablesViewModel) {
    self.wearables = wearables
    self.viewModel = viewModel
  }

  var body: some View {
    if viewModel.registrationState == .registered || viewModel.hasMockDevice {
      TabView(selection: $selectedTab) {
        StreamSessionView(wearables: wearables, wearablesVM: viewModel)
          .tabItem {
            Label("Stream", systemImage: "video")
          }
          .tag(0)
          .accessibilityLabel("Video streaming tab")
          .accessibilityHint("Record video from your glasses")

        LifelogView()
          .tabItem {
            Label("Lifelog", systemImage: "calendar")
          }
          .tag(1)
          .accessibilityLabel("Lifelog tab")
          .accessibilityHint("Browse your recorded memories")

        PhotoGalleryView()
          .tabItem {
            Label("Photos", systemImage: "photo.on.rectangle")
          }
          .tag(2)
          .accessibilityLabel("Photos tab")
          .accessibilityHint("Browse photos captured during recording")

        AudioTestView()
          .tabItem {
            Label("Audio", systemImage: "headphones")
          }
          .tag(3)
          .accessibilityLabel("Audio testing tab")
          .accessibilityHint("Test audio routing to your glasses")
      }
      .task {
        // Sync lifelog with cloud on app launch
        await LifelogSyncManager.shared.sync()
      }
    } else {
      // User not registered - show registration/onboarding flow
      HomeScreenView(viewModel: viewModel)
    }
  }
}
