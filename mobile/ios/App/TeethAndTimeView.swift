import SwiftUI
import OpenSourceOrthoLiteKit

struct TeethAndTimeView: View {
    @EnvironmentObject private var model: LiteFlowViewModel
    @State private var history: SampleHistory?
    @State private var showSample = false
    @State private var arch = "Both"
    @State private var importedIndex = -1
    @State private var progress = 0.0
    @State private var presentation: ScanPresentation?
    @State private var error: String?
    @State private var resetID = 0
    @State private var loadedID = ""

    private var imported: [PreviewScan] { model.previewScans.filter { ["scan","stl"].contains($0.modality) } }
    private var usingSample: Bool { showSample || imported.isEmpty }
    private var chosen: [PreviewScan] {
        importedIndex < 0 ? Array(imported.prefix(2)) : Array(imported.dropFirst(importedIndex).prefix(1))
    }
    private var loadID: String {
        usingSample ? (history?.specimenId ?? "sample") : chosen.map { "\($0.id):\($0.data?.count ?? -1):\($0.error ?? "")" }.joined(separator: ":")
    }
    private var visible: ScanPresentation? {
        guard loadedID == loadID else { return nil }
        return usingSample ? presentation?.selecting(arch) : presentation
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                Text(usingSample ? "\(history?.pseudonym ?? "Sample") · scan comparison" : "Your 3D scans").font(.title2.bold())
                if !imported.isEmpty {
                    Picker("Scan source", selection: $showSample) {
                        Text("Your files").tag(false); Text(history?.pseudonym ?? "Sample").tag(true)
                    }.pickerStyle(.segmented)
                }
                if usingSample {
                    Picker("Arches", selection: $arch) {
                        ForEach(["Both","Upper","Lower"], id: \.self) { Text($0).tag($0) }
                    }.pickerStyle(.segmented)
                    Text(arch == "Both" ? "Upper above · lower below" : "\(arch) arch").font(.caption).foregroundStyle(.secondary)
                } else {
                    Picker("Scan file", selection: $importedIndex) {
                        Text("First two files").tag(-1)
                        ForEach(imported.indices, id: \.self) { Text(imported[$0].fileName).tag($0) }
                    }
                }
                ZStack {
                    Color(red: 0.065, green: 0.09, blue: 0.14)
                    if let visible {
                        ScanSurfaceView(presentation: visible, progress: usingSample ? progress : 0, resetID: resetID)
                    } else if let error { Text(error).foregroundStyle(.white).padding() }
                    else { ProgressView("Loading scans…").tint(.white).foregroundStyle(.white) }
                }.frame(height: arch == "Both" || !usingSample ? 400 : 320)
                    .clipShape(RoundedRectangle(cornerRadius: 18))
                if usingSample {
                    HStack { Text("Baseline"); Spacer(); Text("Week 7") }.font(.subheadline.bold())
                    Slider(value: Binding(get: { progress }, set: { progress = $0 < 0.01 ? 0 : $0 > 0.99 ? 1 : $0 }), in: 0...1).accessibilityLabel("Compare recorded scans")
                    Text(progress == 0 ? "Baseline · \(history?.visits.first?.date ?? "")" : progress == 1 ? "Week 7 · \(history?.visits.last?.date ?? "")" : "Before / after reveal · \(Int(progress*100))% week 7")
                        .font(.caption).accessibilityIdentifier("comparison-status")
                }
                HStack {
                    Text("Drag model to rotate · pinch to zoom").font(.caption).foregroundStyle(.secondary)
                    Spacer(); Button("Reset view") { resetID += 1 }.font(.caption)
                }
                if let visible {
                    let layers = usingSample && progress == 1 ? visible.after : visible.before
                    ForEach(layers.indices, id: \.self) { i in
                        let layer = layers[i]
                        Text("\(usingSample && progress > 0 && progress < 1 ? "Baseline · " : "")\(layer.label): \(layer.mesh.isPointCloud ? "Point cloud" : "Complete surface") · \(layer.mesh.isPointCloud ? layer.mesh.vertexCount : layer.mesh.triangleCount) \(layer.mesh.isPointCloud ? "points" : "triangles")")
                            .font(.caption).accessibilityIdentifier("surface-\(i)")
                    }
                }
                if usingSample {
                    Text("Drag the slider to reveal the two recorded scans. Each arch is positioned separately for viewing, not as a registered bite. No intermediate movement is simulated; scale and registration between visits are unverified.")
                        .font(.caption).foregroundStyle(.secondary)
                } else {
                    Text("Geometry-only preview; textures are not loaded. Point clouds are shown as points. Units are unverified.").font(.caption)
                    if model.scans.allSatisfy(\.isSTL), !model.scans.isEmpty {
                        Button("Generate for review") { Task { await model.generate() } }.disabled(model.isGenerating || visible == nil)
                    } else { Text("Use the browser/full engine for review of other scan formats.").font(.caption) }
                }
                if let message = model.errorMessage { Text(message).font(.caption).foregroundStyle(.red) }
            }.padding()
        }
        .task {
            do {
                guard let url = Bundle.main.url(forResource: "history", withExtension: "json", subdirectory: "sample-history") else { throw CocoaError(.fileNoSuchFile) }
                history = try SampleHistory.decode(Data(contentsOf: url))
            } catch { self.error = "Sample history could not be loaded." }
        }
        .task(id: loadID) { await loadSurface() }
    }
    @MainActor private func loadSurface() async {
        presentation = nil
        guard !usingSample || history != nil else { return }
        guard usingSample || chosen.allSatisfy({ $0.data != nil || $0.error != nil }) else { return }
        let id = loadID, sample = usingSample ? history : nil, scans = chosen
        error = nil
        let task = Task.detached(priority: .userInitiated) {
            if let sample { return try ScanPresentationLoader.sample(sample) }
            return try ScanPresentationLoader.imported(scans)
        }
        do {
            let result = try await withTaskCancellationHandler { try await task.value } onCancel: { task.cancel() }
            guard !Task.isCancelled else { return }
            loadedID = id; presentation = result
        } catch {
            guard !Task.isCancelled else { return }
            self.error = error.localizedDescription
        }
    }
}
