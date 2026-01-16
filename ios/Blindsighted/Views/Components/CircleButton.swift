//
// CircleButton.swift
//
// Reusable circular button component used in streaming controls and UI actions.
//

import SwiftUI

struct CircleButton: View {
  let icon: String
  let text: String?
  let accessibilityLabel: String
  let accessibilityHint: String?
  let action: () -> Void

  init(
    icon: String,
    text: String? = nil,
    accessibilityLabel: String,
    accessibilityHint: String? = nil,
    action: @escaping () -> Void
  ) {
    self.icon = icon
    self.text = text
    self.accessibilityLabel = accessibilityLabel
    self.accessibilityHint = accessibilityHint
    self.action = action
  }

  var body: some View {
    Button(action: action) {
      if let text {
        VStack(spacing: 2) {
          Image(systemName: icon)
            .font(.system(size: 14))
          Text(text)
            .font(.system(size: 10, weight: .medium))
        }
      } else {
        Image(systemName: icon)
          .font(.system(size: 16))
      }
    }
    .foregroundColor(.black)
    .frame(width: 56, height: 56)
    .background(.white)
    .clipShape(Circle())
    .accessibilityLabel(accessibilityLabel)
    .accessibilityHint(accessibilityHint ?? "")
  }
}
