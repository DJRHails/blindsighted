//
// CardView.swift
//
// Reusable container component that provides consistent card styling throughout the app.
//

import SwiftUI

struct CardView<Content: View>: View {
  let content: Content

  init(@ViewBuilder content: () -> Content) {
    self.content = content()
  }

  var body: some View {
    VStack(spacing: 0) {
      content
    }
    .background(Color(.systemBackground))
    .cornerRadius(12)
    .shadow(
      color: Color.black.opacity(0.1),
      radius: 4,
      x: 0,
      y: 2
    )
  }
}
