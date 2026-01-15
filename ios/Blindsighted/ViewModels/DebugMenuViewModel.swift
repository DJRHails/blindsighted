//
// DebugMenuViewModel.swift
//
// Debug-only view model that provides access to mock devices for development and testing.
// This enables developers to test DAT SDK streaming functionality without physical Meta
// wearable devices. Mock devices simulate the behavior of real devices, allowing for
// comprehensive testing of streaming, photo capture, and error handling workflows.
//

#if DEBUG

import MWDATMockDevice
import SwiftUI

@MainActor
class DebugMenuViewModel: ObservableObject {
  @Published public var showDebugMenu: Bool
  @Published public var mockDeviceKitViewModel: MockDeviceKitView.ViewModel

  init(mockDeviceKit: MockDeviceKitInterface) {
    self.mockDeviceKitViewModel = MockDeviceKitView.ViewModel(mockDeviceKit: mockDeviceKit)
    self.showDebugMenu = false
  }
}

#endif
