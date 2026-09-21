import SwiftUI
import CryptoKit
import OpenSourceOrthoLiteKit

/// Observed scans only. Viewing the sample never changes the uploaded case.
struct TeethAndTimeView: View {
    @EnvironmentObject private var model: LiteFlowViewModel
    @State private var history: SampleHistory?
    @State private var visitIndex = 0
    @State private var archIndex = 0
    @State private var importedIndex = 0
    @State private var showSample = false
    @State private var mesh: STLMesh?
    @State private var error: String?
    @State private var resetID = 0

    private var imported: [PreviewScan] { model.previewScans.filter { $0.modality == "stl" } }
    private var usingSample: Bool { showSample || imported.isEmpty }
    private var visit: SampleHistory.Visit? { history?.visits[visitIndex] }
    private var arch: SampleHistory.Arch? { visit?.arches[archIndex] }
    private var loadID: String {
        usingSample ? (arch?.sha256 ?? "sample") : imported[min(importedIndex, imported.count - 1)].id.uuidString
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 14) {
                Text(usingSample ? "\(history?.pseudonym ?? "Sample") · scan history" : "Your scan")
                    .font(.title2.bold())
                if !imported.isEmpty {
                    Picker("Scan source", selection: $showSample) {
                        Text("Your files").tag(false)
                        Text(history?.pseudonym ?? "Sample").tag(true)
                    }.pickerStyle(.segmented)
                }
                if usingSample, let history, let visit {
                    Picker("Recorded visit", selection: $visitIndex) {
                        ForEach(history.visits.indices, id: \.self) { i in Text(history.visits[i].label).tag(i) }
                    }.pickerStyle(.segmented)
                    Picker("Arch", selection: $archIndex) {
                        ForEach(visit.arches.indices, id: \.self) { i in Text(visit.arches[i].name).tag(i) }
                    }.pickerStyle(.segmented)
                    Text("\(visit.label) · \(visit.date)").font(.subheadline).foregroundStyle(.secondary)
                } else if !imported.isEmpty {
                    Picker("Scan file", selection: $importedIndex) {
                        ForEach(imported.indices, id: \.self) { i in Text(imported[i].fileName).tag(i) }
                    }
                }
                ZStack {
                    Color(red: 0.07, green: 0.10, blue: 0.15)
                    if let mesh {
                        ScanSurfaceView(mesh: mesh, rotation: usingSample ? (arch?.displayRotation ?? [1,1,1]) : [1,1,1], resetID: resetID)
                            .id(loadID)
                    } else if let error {
                        Text(error).foregroundStyle(.white).padding()
                    } else {
                        ProgressView("Loading scan…").tint(.white).foregroundStyle(.white)
                    }
                }
                .frame(height: 320).clipShape(RoundedRectangle(cornerRadius: 18))
                HStack {
                    Text("Drag to rotate · pinch to zoom").font(.caption).foregroundStyle(.secondary)
                    Spacer()
                    Button("Reset view") { resetID += 1 }.font(.caption)
                }
                if let mesh {
                    Text("Complete STL surface · \(mesh.triangleCount.formatted()) triangles").font(.caption)
                }
                if usingSample, let visit {
                    Text(visit.detail).font(.subheadline)
                    Text("Two recorded visits. Each arch is fitted independently to the view. Scale and registration between visits are unverified; no tooth movement is inferred.")
                        .font(.caption).foregroundStyle(.secondary)
                } else {
                    Text("Original uploaded geometry. No simulated movement is applied.").font(.caption)
                    Button("Generate for review") { Task { await model.generate() } }
                        .buttonStyle(.borderedProminent).disabled(model.isGenerating)
                }
                if let message = model.errorMessage { Text(message).font(.caption).foregroundStyle(.red) }
            }.padding()
        }
        .task {
            do {
                guard let url = Bundle.main.url(forResource: "history", withExtension: "json", subdirectory: "sample-history") else {
                    throw CocoaError(.fileNoSuchFile)
                }
                history = try SampleHistory.decode(Data(contentsOf: url))
            } catch { self.error = "Sample history could not be loaded." }
        }
        .task(id: loadID) { await loadSurface() }
    }

    @MainActor private func loadSurface() async {
        mesh = nil
        guard !usingSample || arch != nil else { return }
        error = nil
        let selectedArch = usingSample ? arch : nil
        let importedData = usingSample ? nil : imported[min(importedIndex, imported.count - 1)].data
        let task = Task.detached(priority: .userInitiated) { () throws -> STLMesh in
            let data: Data
            if let selectedArch {
                guard let url = Bundle.main.url(forResource: selectedArch.filename, withExtension: nil) else {
                    throw CocoaError(.fileNoSuchFile)
                }
                data = try Data(contentsOf: url)
                let hash = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
                guard hash == selectedArch.sha256 else { throw STLMesh.LoadError.invalid }
            } else if let importedData { data = importedData }
            else { throw STLMesh.LoadError.invalid }
            return try STLMesh.decode(data)
        }
        do {
            let result = try await withTaskCancellationHandler {
                try await task.value
            } onCancel: { task.cancel() }
            guard !Task.isCancelled else { return }
            mesh = result
        } catch {
            guard !Task.isCancelled else { return }
            self.error = error.localizedDescription
        }
    }
}
