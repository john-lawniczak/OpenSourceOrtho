import SwiftUI
import OpenSourceOrthoLiteKit

struct SampleHistoryView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var history: SampleHistory?
    @State private var error: String?
    @State private var visitIndex = 0

    var body: some View {
        NavigationStack {
            ScrollView {
                if let history {
                    historyContent(history)
                } else {
                    Text(error ?? "Loading sample history…").padding()
                }
            }
            .navigationTitle("Sample history")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .confirmationAction) { Button("Done") { dismiss() } } }
        }
        .task { loadHistory() }
    }

    private func historyContent(_ history: SampleHistory) -> some View {
        let visit = history.visits[visitIndex]
        return VStack(alignment: .leading, spacing: 16) {
            Text(history.summary).font(.headline)
            Picker("Scan visit", selection: $visitIndex) {
                ForEach(history.visits.indices, id: \.self) { index in
                    Text(history.visits[index].label).tag(index)
                }
            }
            .pickerStyle(.segmented)
            Text("\(visit.label) · \(visit.date)").font(.title3.bold())
            Text(visit.detail).font(.subheadline)
            Text(history.limitation).font(.footnote).foregroundStyle(.secondary)
            ForEach(visit.arches, id: \.filename) { arch in
                archCard(arch, visit: visit)
            }
            Text("Recorded timeline").font(.headline)
            ForEach(history.events) { event in
                VStack(alignment: .leading, spacing: 3) {
                    Text(event.label).font(.subheadline.bold())
                    Text(event.date).font(.caption).foregroundStyle(.secondary)
                }
            }
            Text(history.timing).font(.footnote)
            Text(history.context).font(.footnote).foregroundStyle(.secondary)
            Text("Research sample · final outcome not recorded").font(.footnote.bold())
        }
        .padding()
    }

    private func archCard(_ arch: SampleHistory.Arch, visit: SampleHistory.Visit) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("\(arch.name) arch").font(.headline)
            if let url = Bundle.main.url(forResource: arch.previewImage, withExtension: nil,
                                          subdirectory: "sample-history"),
               let image = UIImage(contentsOfFile: url.path) {
                Image(uiImage: image).resizable().scaledToFit()
                    .accessibilityLabel("\(visit.label), \(arch.name.lowercased()) scan surface, independent view")
            } else {
                Text("Scan preview unavailable").foregroundStyle(.secondary)
            }
            Text("\(arch.faceCount) triangles · \(arch.zeroAreaFaces) zero-area faces")
                .font(.caption)
            Text(arch.units == "mm" ? "Recorded units: mm" : "Physical scale unverified")
                .font(.caption).foregroundStyle(.secondary)
            Text("View rendered from the original STL. No intermediate scans are inferred.")
                .font(.caption).foregroundStyle(.secondary)
        }
    }

    private func loadHistory() {
        do {
            guard let url = Bundle.main.url(forResource: "history", withExtension: "json",
                                             subdirectory: "sample-history") else {
                throw CocoaError(.fileNoSuchFile)
            }
            history = try SampleHistory.decode(Data(contentsOf: url))
        } catch {
            self.error = "Sample history could not be loaded."
        }
    }
}
