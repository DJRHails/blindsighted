//
// DebugMenuView.swift
//
// Debug-only overlay that provides access to mock device functionality during development.
// This view demonstrates how to integrate mock devices for testing DAT SDK features
// without requiring physical Meta wearable devices.
//

#if DEBUG

import SwiftUI

struct DebugMenuView: View {
  @ObservedObject var debugMenuViewModel: DebugMenuViewModel
  @State private var position: CGPoint = .zero
  @State private var isDragging = false

  private let buttonSize: CGFloat = 60

  var body: some View {
    GeometryReader { geometry in
      Button(action: {
        debugMenuViewModel.showDebugMenu = true
      }) {
        Image(systemName: "ladybug.fill")
          .foregroundColor(.white)
          .padding()
          .background(.secondary)
          .clipShape(Circle())
          .shadow(radius: 4)
      }
      .accessibilityIdentifier("debug_menu_button")
      .frame(width: buttonSize, height: buttonSize)
      .position(
        x: position.x == 0 ? geometry.size.width - buttonSize / 2 - 20 : position.x,
        y: position.y == 0 ? geometry.size.height / 2 : position.y
      )
      .gesture(
        DragGesture()
          .onChanged { value in
            isDragging = true
            // Allow free movement while dragging
            let newX = max(buttonSize / 2, min(value.location.x, geometry.size.width - buttonSize / 2))
            let newY = max(buttonSize / 2, min(value.location.y, geometry.size.height - buttonSize / 2))
            position = CGPoint(x: newX, y: newY)
          }
          .onEnded { value in
            isDragging = false
            // Snap to nearest edge
            snapToNearestEdge(in: geometry.size)
          }
      )
    }
  }

  private func snapToNearestEdge(in size: CGSize) {
    let padding: CGFloat = 20
    let halfButton = buttonSize / 2

    // Calculate distances to each edge
    let distanceToLeft = position.x - halfButton
    let distanceToRight = size.width - position.x - halfButton
    let distanceToTop = position.y - halfButton
    let distanceToBottom = size.height - position.y - halfButton

    // Find minimum distance
    let minDistance = min(distanceToLeft, distanceToRight, distanceToTop, distanceToBottom)

    // Snap to the nearest edge
    withAnimation(.spring(response: 0.3, dampingFraction: 0.7)) {
      switch minDistance {
      case distanceToLeft:
        position.x = halfButton + padding
      case distanceToRight:
        position.x = size.width - halfButton - padding
      case distanceToTop:
        position.y = halfButton + padding
      default: // distanceToBottom
        position.y = size.height - halfButton - padding
      }
    }
  }
}

#endif
