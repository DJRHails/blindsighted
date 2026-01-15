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

        VideoGalleryView()
          .tabItem {
            Label("Gallery", systemImage: "square.grid.2x2")
          }
          .tag(1)
      }
    } else {
      // User not registered - show registration/onboarding flow
      HomeScreenView(viewModel: viewModel)
    }
  }
}
