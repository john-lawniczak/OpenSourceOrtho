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
                stepContent
            }
            .navigationTitle("OpenSource Ortho")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                Button {
                    isShowingSettings = true
                } label: {
                    Image(systemName: "gearshape")
                }
                .accessibilityLabel("Settings")
            }
            .sheet(isPresented: $isShowingSettings) {
                SettingsView()
            }
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
