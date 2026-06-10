import SwiftUI
import SceneKit
import UIKit
import UniformTypeIdentifiers
import OpenSourceOrthoLiteKit

// Lite-flow screens. These are scaffolding: they wire the flow and render engine
// output. The STL file picker and the real 3D renderer are marked TODO - see
// ../README.md "What still has to be built".

/// Step 1: pick CBCT, STL, or photo records from the device.
struct UploadView: View {
    @EnvironmentObject private var model: LiteFlowViewModel
    @State private var importer: ImporterKind?

    private enum ImporterKind: Identifiable {
        case cbct, stl, photo

        var id: String { modality }

        var modality: String {
            switch self {
            case .cbct: return "cbct"
            case .stl: return "stl"
            case .photo: return "photo"
            }
        }

        var allowedTypes: [UTType] {
            switch self {
            case .cbct:
                var types: [UTType] = [.zip, .data]
                if let dicom = UTType(filenameExtension: "dcm") {
                    types.append(dicom)
                }
                return types
            case .stl:
                return [UTType(filenameExtension: "stl") ?? .data]
            case .photo:
                return [.image]
            }
        }
    }

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "square.and.arrow.up")
                .font(.system(size: 48))
                .foregroundStyle(.tint)
            Text("Upload patient files")
                .font(.title3.bold())
            Text("CBCT is preferred when available. STL scans work well. General photos can support review notes.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            VStack(spacing: 10) {
                Button("Add CBCT / DICOM") {
                    importer = .cbct
                }
                Button("Add STL scan") {
                    importer = .stl
                }
                Button("Add photos") {
                    importer = .photo
                }
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
        .frame(maxHeight: .infinity)
        .fileImporter(
            isPresented: Binding(
                get: { importer != nil },
                set: { if !$0 { importer = nil } }
            ),
            allowedContentTypes: importer?.allowedTypes ?? [.data],
            allowsMultipleSelection: true
        ) { result in
            guard let importer else { return }
            if case let .success(urls) = result {
                for url in urls {
                    model.addFile(url: url, modality: importer.modality)
                }
            }
            self.importer = nil
        }
    }
}

/// Step 2: staged teeth preview and timeline controls.
struct TeethAndTimeView: View {
    @EnvironmentObject private var model: LiteFlowViewModel
    @State private var stage = 0.0

    var body: some View {
        VStack(spacing: 16) {
            Text("Teeth + time")
                .font(.title3.bold())
            DentalScenePreview(stage: stage)
                .frame(height: 280)
                .clipShape(RoundedRectangle(cornerRadius: 12))
            Slider(value: $stage, in: 0...12, step: 1)
            Text("Stage \(Int(stage)) of 12")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text("\(model.scans.count) file(s) selected")
                .font(.headline)
            if let error = model.errorMessage {
                Text(error).font(.footnote).foregroundStyle(.red).multilineTextAlignment(.center)
            }
            Button {
                Task { await model.generate() }
            } label: {
                if model.isGenerating { ProgressView() } else { Text("Generate for review") }
            }
            .buttonStyle(.borderedProminent)
            .disabled(model.isGenerating)
        }
        .padding()
        .frame(maxHeight: .infinity)
    }
}

/// Step 3: engine verdict + steps. Verdict is CONSISTENT/ISSUES only.
struct ReviewView: View {
    @EnvironmentObject private var model: LiteFlowViewModel

    var body: some View {
        List {
            if let verdict = model.result?.correctness?.verdict {
                Section("Engine verdict") {
                    Text(SafetyText.verdictLabel(verdict)).font(.headline)
                }
            }
            if let steps = model.result?.steps, !steps.isEmpty {
                Section("Pipeline") {
                    ForEach(steps) { step in
                        VStack(alignment: .leading) {
                            Text(step.name).font(.subheadline.bold())
                            Text("\(step.status): \(step.detail)")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
            }
            if let caveat = model.result?.caveat {
                Section { Text(caveat).font(.footnote).foregroundStyle(.secondary) }
            }
            Section {
                Button("Print and send") { model.showPrintAndSend() }
            }
        }
    }
}

/// Step 4: export package for print / 3D-printer handoff.
struct PrintAndSendView: View {
    @EnvironmentObject private var model: LiteFlowViewModel
    @State private var packageURL: URL?
    @State private var exportError: String?

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "printer")
                .font(.system(size: 44))
                .foregroundStyle(.tint)
            Text("Print and send")
                .font(.title3.bold())
            Text("Export the generated package for clinician review, lab handoff, or 3D-printer preparation.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            if let packageURL {
                ShareLink(item: packageURL) {
                    Label("Export print package", systemImage: "square.and.arrow.up")
                }
                .buttonStyle(.borderedProminent)
                ShareLink(item: packageURL) {
                    Label("Send to 3D printer", systemImage: "printer")
                }
                .buttonStyle(.bordered)
            } else {
                Button {
                    preparePackage()
                } label: {
                    Label("Prepare package", systemImage: "doc.badge.gearshape")
                }
                .buttonStyle(.borderedProminent)
            }
            if let exportError {
                Text(exportError)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .multilineTextAlignment(.center)
            }
            Button("Start over") { model.reset() }
        }
        .padding()
        .frame(maxHeight: .infinity)
        .onAppear(perform: preparePackage)
    }

    private func preparePackage() {
        do {
            packageURL = try model.exportPackageURL()
            exportError = nil
        } catch {
            exportError = "Could not prepare export package: \(error.localizedDescription)"
        }
    }
}

struct DentalScenePreview: View {
    var stage: Double

    var body: some View {
        SceneView(
            scene: DentalPreviewScene.make(stage: stage),
            options: [.allowsCameraControl, .autoenablesDefaultLighting]
        )
    }
}

private enum DentalPreviewScene {
    static func make(stage: Double) -> SCNScene {
        let scene = SCNScene()
        scene.background.contents = UIColor.systemBackground

        let camera = SCNCamera()
        camera.fieldOfView = 45
        let cameraNode = SCNNode()
        cameraNode.camera = camera
        cameraNode.position = SCNVector3(0, 0, 9)
        scene.rootNode.addChildNode(cameraNode)

        let light = SCNLight()
        light.type = .omni
        light.intensity = 900
        let lightNode = SCNNode()
        lightNode.light = light
        lightNode.position = SCNVector3(0, 3, 6)
        scene.rootNode.addChildNode(lightNode)

        addArch(to: scene, y: 0.85, stage: stage, isUpper: true)
        addArch(to: scene, y: -0.85, stage: stage, isUpper: false)
        return scene
    }

    private static func addArch(to scene: SCNScene, y: Float, stage: Double, isUpper: Bool) {
        let progress = Float(stage / 12.0)
        for index in 0..<8 {
            let centered = Float(index) - 3.5
            let tooth = SCNSphere(radius: 0.22)
            tooth.segmentCount = 18
            tooth.firstMaterial?.diffuse.contents = UIColor.systemTeal.withAlphaComponent(isUpper ? 0.95 : 0.75)

            let node = SCNNode(geometry: tooth)
            let curve = sin((Float(index) / 7.0) * .pi) * 0.65
            let direction: Float = centered >= 0 ? 1 : -1
            let xOffset = (isUpper ? 0.12 : -0.12) * progress * direction
            node.position = SCNVector3(centered * 0.48 + xOffset, y + curve * (isUpper ? 1 : -1), 0)
            node.scale = SCNVector3(1.0, 1.25, 0.75)
            scene.rootNode.addChildNode(node)
        }
    }
}

struct GlossaryView: View {
    private let terms = [
        ("CBCT", "Cone-beam CT. Best source when roots, bone, or impacted teeth matter."),
        ("STL", "Surface mesh from an intraoral scan or model scan."),
        ("Stage", "One planned tooth-position step in the timeline."),
        ("Attachment", "A planned shape bonded to a tooth to help aligner force delivery."),
        ("IPR", "Interproximal reduction, measured space created between teeth."),
    ]

    var body: some View {
        List(terms, id: \.0) { term, definition in
            VStack(alignment: .leading, spacing: 4) {
                Text(term).font(.headline)
                Text(definition).font(.subheadline).foregroundStyle(.secondary)
            }
        }
        .navigationTitle("Glossary")
    }
}

struct TeethMapView: View {
    private let upper = ["18", "17", "16", "15", "14", "13", "12", "11", "21", "22", "23", "24", "25", "26", "27", "28"]
    private let lower = ["48", "47", "46", "45", "44", "43", "42", "41", "31", "32", "33", "34", "35", "36", "37", "38"]

    var body: some View {
        List {
            Section("Upper arch") {
                LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 4)) {
                    ForEach(upper, id: \.self) { Text($0).padding(8) }
                }
            }
            Section("Lower arch") {
                LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 4)) {
                    ForEach(lower, id: \.self) { Text($0).padding(8) }
                }
            }
        }
        .navigationTitle("Teeth Map")
    }
}
