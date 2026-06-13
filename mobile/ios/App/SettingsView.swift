import SwiftUI

enum AppTheme: String, CaseIterable, Identifiable {
    case system
    case light
    case dark

    var id: String { rawValue }

    var title: String {
        switch self {
        case .system: return "System"
        case .light: return "Light"
        case .dark: return "Dark"
        }
    }

    var colorScheme: ColorScheme? {
        switch self {
        case .system: return nil
        case .light: return .light
        case .dark: return .dark
        }
    }
}

struct SettingsView: View {
    @AppStorage("liteAppearanceTheme") private var themeRawValue = AppTheme.system.rawValue

    var body: some View {
        List {
            Section("About") {
                HStack {
                    Text("OpenSource Ortho Lite")
                    Spacer()
                    Text(AppIdentity.installedVersionDisplay)
                        .foregroundStyle(.secondary)
                }
                .accessibilityElement(children: .combine)
                NavigationLink("Mobile app and browser accuracy", destination: MobileAppInfoView())
            }
            Section("Appearance") {
                Picker("Theme", selection: $themeRawValue) {
                    ForEach(AppTheme.allCases) { theme in
                        Text(theme.title).tag(theme.rawValue)
                    }
                }
                Text("Dark mode can increase contrast for the mobile STL teeth preview.")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Section("Reference") {
                NavigationLink("Glossary", destination: GlossaryView())
                NavigationLink("Teeth map", destination: TeethMapView())
            }
        }
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
    }
}

private struct MobileAppInfoView: View {
    var body: some View {
        List {
            Section("What this app is") {
                Text("OpenSource Ortho Lite is a mobile review and handoff companion for OpenSource Ortho. It can collect files, show a lightweight preview, run or import review summaries, and export a package for sharing.")
                Text("It is not a diagnostic app, not treatment approval, and not a manufacturing clearance tool.")
                    .foregroundStyle(.secondary)
            }
            Section("Why the browser is more accurate") {
                Text("The full browser workspace uses the local engine and larger-screen 3D tools for higher-fidelity rendering, segmentation review, setup comparison, restaging, print-package QA, and file-size-heavy STL/CBCT workflows.")
                Text("Mobile previews intentionally downshift when files are large, unsupported, or missing reviewed per-tooth geometry. Use the browser/full engine for print-critical review and detailed geometry checks.")
                    .foregroundStyle(.secondary)
            }
            Section("Best use") {
                Text("Use mobile for intake, quick review, glossary lookup, case handoff, and sharing. Use the browser for detailed plan edits, rendering accuracy, segmentation, and final export review.")
            }
        }
        .navigationTitle("Mobile and Browser")
        .navigationBarTitleDisplayMode(.inline)
    }
}
