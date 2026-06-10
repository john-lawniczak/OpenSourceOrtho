import SwiftUI

struct SettingsView: View {
    var body: some View {
        NavigationStack {
            List {
                Section("About") {
                    HStack {
                        Text("OpenSource Ortho Lite")
                        Spacer()
                        Text(AppIdentity.installedVersionDisplay)
                            .foregroundStyle(.secondary)
                    }
                    .accessibilityElement(children: .combine)
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
}
