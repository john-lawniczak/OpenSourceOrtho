import SwiftUI
import OpenSourceOrthoLiteKit

/// Top-level lite UI: a standing safety banner plus the current flow step.
/// Screens are intentionally thin - they render engine output, never compute it.
struct RootView: View {
    @EnvironmentObject private var model: LiteFlowViewModel
    @State private var isShowingSettings = false

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                SafetyBanner()
                Divider()
                if isShowingSettings {
                    SettingsView()
                } else {
                    stepContent
                }
                Divider()
                BottomNavigationBar(
                    selectedStep: model.step,
                    isShowingSettings: isShowingSettings,
                    onSelectStep: { step in
                        isShowingSettings = false
                        model.navigate(to: step)
                    },
                    onSelectSettings: {
                        isShowingSettings = true
                    }
                )
            }
            .navigationTitle("OpenSource Ortho")
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    @ViewBuilder
    private var stepContent: some View {
        switch model.step {
        case .upload:       UploadView()
        case .teethAndTime: TeethAndTimeView()
        case .review:       ReviewView()
        case .printAndSend: PrintAndSendView()
        }
    }
}

private struct BottomNavigationBar: View {
    var selectedStep: LiteStep
    var isShowingSettings: Bool
    var onSelectStep: (LiteStep) -> Void
    var onSelectSettings: () -> Void

    var body: some View {
        HStack(spacing: 0) {
            BottomNavigationButton(
                title: "Upload",
                systemImage: "square.and.arrow.up",
                isSelected: !isShowingSettings && selectedStep == .upload
            ) { onSelectStep(.upload) }
            BottomNavigationButton(
                title: "Teeth",
                systemImage: "cube.transparent",
                isSelected: !isShowingSettings && selectedStep == .teethAndTime
            ) { onSelectStep(.teethAndTime) }
            BottomNavigationButton(
                title: "Review",
                systemImage: "checklist",
                isSelected: !isShowingSettings && selectedStep == .review
            ) { onSelectStep(.review) }
            BottomNavigationButton(
                title: "Print",
                systemImage: "printer",
                isSelected: !isShowingSettings && selectedStep == .printAndSend
            ) { onSelectStep(.printAndSend) }
            BottomNavigationButton(
                title: "Settings",
                systemImage: "gearshape",
                isSelected: isShowingSettings,
                action: onSelectSettings
            )
        }
        .padding(.horizontal, 8)
        .padding(.top, 6)
        .padding(.bottom, 8)
        .background(.bar)
    }
}

private struct BottomNavigationButton: View {
    var title: String
    var systemImage: String
    var isSelected: Bool
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 4) {
                Image(systemName: systemImage)
                    .font(.system(size: 18, weight: isSelected ? .semibold : .regular))
                Text(title)
                    .font(.caption2)
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity)
            .foregroundStyle(isSelected ? Color.accentColor : Color.secondary)
            .padding(.vertical, 4)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(title)
    }
}

/// Non-dismissible disclaimer, wording sourced from the kit (kept in sync with
/// the engine `caveat`). Required by the project safety boundary.
struct SafetyBanner: View {
    var body: some View {
        Text(SafetyText.disclaimer)
            .font(.footnote)
            .foregroundStyle(.secondary)
            .padding(12)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(.yellow.opacity(0.12))
    }
}
