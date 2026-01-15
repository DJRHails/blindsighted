

//
// CustomButton.swift
//
// Reusable button component used throughout the Blindsighted app for consistent styling.
//

import SwiftUI

struct CustomButton: View {
  let title: String
  let style: ButtonStyle
  let isDisabled: Bool
  let action: () -> Void

  enum ButtonStyle {
    case primary, destructive

    var backgroundColor: Color {
      switch self {
      case .primary:
        return .appPrimary
      case .destructive:
        return .destructiveBackground
      }
    }

    var foregroundColor: Color {
      switch self {
      case .primary:
        return .white
      case .destructive:
        return .destructiveForeground
      }
    }
  }

  var body: some View {
    Button(action: action) {
      Text(title)
        .font(.system(size: 15, weight: .semibold))
        .foregroundColor(style.foregroundColor)
        .frame(maxWidth: .infinity)
        .frame(height: 56)
        .background(style.backgroundColor)
        .cornerRadius(30)
    }
    .disabled(isDisabled)
    .opacity(isDisabled ? 0.6 : 1.0)
  }
}
