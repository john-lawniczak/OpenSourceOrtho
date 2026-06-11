import SwiftUI
import SceneKit
import UIKit
import UniformTypeIdentifiers
import PhotosUI
import OpenSourceOrthoLiteKit

// Lite-flow screens. These are scaffolding: they wire the flow and render engine
// output. Mobile can synthesize a limited STL-only review if the engine is
// offline; CBCT/DICOM and mesh-backed edits remain browser/full-engine work.

/// Step 1: pick scan records, supporting photos, or browser-generated review packages.
struct UploadView: View {
    @EnvironmentObject private var model: LiteFlowViewModel
    @State private var importer: ImporterKind?
    @State private var photoItems: [PhotosPickerItem] = []

    private enum ImporterKind: Identifiable {
        case stl, cbct, photoFiles, browserReview

        var id: String { modality }

        var modality: String {
            switch self {
            case .stl: return "stl"
            case .cbct: return "cbct"
            case .photoFiles: return "photo"
            case .browserReview: return "browser-review"
            }
        }

        var allowedTypes: [UTType] {
            switch self {
            case .stl:
                return [UTType(filenameExtension: "stl") ?? .data]
            case .cbct:
                var types: [UTType] = [.zip, .data]
                if let dicom = UTType(filenameExtension: "dcm") {
                    types.append(dicom)
                }
                return types
            case .photoFiles:
                return [.image]
            case .browserReview:
                return [UTType(filenameExtension: "json") ?? .json]
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
            Text("Mobile renders selected STL scans for review. CBCT/DICOM can be attached for engine/browser handoff; full volume review still needs the browser/full engine.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            VStack(spacing: 10) {
                Button("Add STL scan") {
                    importer = .stl
                }
                Button("Add CBCT / DICOM") {
                    importer = .cbct
                }
                PhotosPicker(selection: $photoItems, maxSelectionCount: 12, matching: .images) {
                    Text("Add photos from library")
                        .frame(maxWidth: .infinity)
                }
                Button("Browse photos in Files, iCloud, or Drive") {
                    importer = .photoFiles
                }
                Button("Import browser review") {
                    importer = .browserReview
                }
                Button("Use dev sample STL") {
                    model.addDevSampleSTL()
                }
            }
            .buttonStyle(.borderedProminent)
            if !model.storedReviews.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Stored browser reviews")
                        .font(.headline)
                    ForEach(model.storedReviews) { review in
                        Text("\(review.fileName) - \(review.byteCount) bytes")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
        }
        .onChange(of: photoItems) { items in
            for (index, item) in items.enumerated() {
                Task {
                    if let data = try? await item.loadTransferable(type: Data.self) {
                        await MainActor.run {
                            model.addPhotoData(fileName: "photo-\(index + 1).jpg", data: data)
                        }
                    }
                }
            }
            photoItems = []
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
                    switch importer {
                    case .stl, .cbct, .photoFiles:
                        model.addFile(url: url, modality: importer.modality)
                    case .browserReview:
                        model.importBrowserReview(url: url)
                    }
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
            DentalScenePreview(stage: stage, scans: model.previewScans)
                .frame(height: 340)
                .clipShape(RoundedRectangle(cornerRadius: 12))
            Slider(value: $stage, in: 0...12, step: 1)
            Text("Stage \(Int(stage)) of 12")
                .font(.subheadline)
                .foregroundStyle(.secondary)
            Text("\(model.scans.count) file(s) selected")
                .font(.headline)
            Text("STL scans render from the selected file when available. CBCT/DICOM is attached for engine/browser review; native volume rendering is not in lite yet.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
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
            if let warnings = model.result?.warnings, !warnings.isEmpty {
                Section("Mobile limits") {
                    ForEach(warnings, id: \.self) { warning in
                        Text(warning).font(.caption).foregroundStyle(.secondary)
                    }
                }
            }
            if !model.storedReviews.isEmpty {
                Section("Stored browser reviews") {
                    ForEach(model.storedReviews) { review in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(review.fileName).font(.subheadline.bold())
                            Text("\(review.byteCount) bytes stored on this device for review/sharing. Open the browser workspace to edit the source plan.")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
            }
            Section("Tray estimate") {
                let trayCount = estimatedTrayCount
                LabeledContent("Initial trays", value: "\(trayCount)")
                if let timeline = model.result?.timeline {
                    LabeledContent("Wear interval", value: "\(timeline.wearIntervalDays) days")
                    LabeledContent(
                        "Projected duration",
                        value: String(format: "%.1f weeks", timeline.projectedDurationWeeks)
                    )
                } else {
                    Text("Generate a review to estimate trays from the engine timeline.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            Section("Refinement options") {
                RefinementRow(title: "No refinement", detail: "Proceed with the initial generated sequence for review.")
                RefinementRow(title: "Mid-course scan", detail: "Add a new STL/CBCT record if tracking drifts from plan.")
                RefinementRow(title: "Attachment/IPR review", detail: "Flag the plan for clinician review of auxiliaries and spacing.")
                RefinementRow(title: "Additional trays", detail: "Plan a second pass after reviewing the final-stage fit.")
            }
            Section {
                Button("Print and send") { model.showPrintAndSend() }
            }
        }
    }

    private var estimatedTrayCount: Int {
        model.result?.timeline?.stageCount ?? model.result?.stageCount ?? max(1, model.scans.count * 6)
    }
}

private struct RefinementRow: View {
    var title: String
    var detail: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(title).font(.subheadline.bold())
            Text(detail).font(.caption).foregroundStyle(.secondary)
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
    var scans: [PreviewScan]

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            SceneView(
                scene: DentalPreviewScene.make(stage: stage, scans: scans),
                options: [.allowsCameraControl, .autoenablesDefaultLighting]
            )
            Text(previewCaption)
                .font(.caption)
                .padding(8)
                .background(.thinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .padding(10)
        }
    }

    private var previewCaption: String {
        if scans.contains(where: { $0.modality.lowercased() == "stl" }) {
            return "Rendering selected STL geometry"
        }
        if scans.contains(where: { $0.modality.lowercased() == "cbct" }) {
            return "CBCT attached; open browser/full engine for volume rendering"
        }
        return "Add an STL scan to render patient geometry"
    }
}

private enum DentalPreviewScene {
    static func make(stage: Double, scans: [PreviewScan]) -> SCNScene {
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

        let stlNodes = scans
            .filter { $0.modality.lowercased() == "stl" }
            .prefix(2)
            .compactMap { STLSceneMesh.node(from: $0.data) }
        if stlNodes.isEmpty {
            addArch(to: scene, y: 0.85, stage: stage, isUpper: true)
            addArch(to: scene, y: -0.85, stage: stage, isUpper: false)
        } else {
            let parent = SCNNode()
            for (index, node) in stlNodes.enumerated() {
                node.position.y = Float(index) * -1.15 + (stlNodes.count == 1 ? 0 : 0.55)
                parent.addChildNode(node)
            }
            centerAndScale(parent)
            scene.rootNode.addChildNode(parent)
        }
        return scene
    }

    private static func centerAndScale(_ node: SCNNode) {
        let bounds = node.boundingBox
        let min = bounds.min
        let maxPoint = bounds.max
        let center = SCNVector3((min.x + maxPoint.x) / 2, (min.y + maxPoint.y) / 2, (min.z + maxPoint.z) / 2)
        let span = Swift.max(maxPoint.x - min.x, Swift.max(maxPoint.y - min.y, maxPoint.z - min.z))
        let scale = span > 0 ? 4.8 / span : 1
        node.position = SCNVector3(-center.x * scale, -center.y * scale, -center.z * scale)
        node.scale = SCNVector3(scale, scale, scale)
        node.eulerAngles.x = -.pi / 2
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

private enum STLSceneMesh {
    static func node(from data: Data) -> SCNNode? {
        let triangles = parseTriangles(from: data)
        guard !triangles.isEmpty else { return nil }
        let vertices = triangles.flatMap { $0 }
        let source = SCNGeometrySource(vertices: vertices)
        let indices = Array(Int32(0)..<Int32(vertices.count))
        let indexData = indices.withUnsafeBufferPointer { Data(buffer: $0) }
        let element = SCNGeometryElement(
            data: indexData,
            primitiveType: .triangles,
            primitiveCount: vertices.count / 3,
            bytesPerIndex: MemoryLayout<Int32>.size
        )
        let geometry = SCNGeometry(sources: [source], elements: [element])
        geometry.firstMaterial?.diffuse.contents = UIColor(red: 0.94, green: 0.88, blue: 0.74, alpha: 1.0)
        geometry.firstMaterial?.specular.contents = UIColor.white
        geometry.firstMaterial?.isDoubleSided = true
        return SCNNode(geometry: geometry)
    }

    private static func parseTriangles(from data: Data) -> [[SCNVector3]] {
        if let ascii = String(data: data.prefix(1024 * 1024), encoding: .utf8), ascii.contains("vertex") {
            let vertices = ascii
                .split(separator: "\n")
                .compactMap { line -> SCNVector3? in
                    let parts = line.trimmingCharacters(in: .whitespaces).split(separator: " ")
                    guard parts.first == "vertex", parts.count >= 4,
                          let x = Float(parts[1]), let y = Float(parts[2]), let z = Float(parts[3]) else {
                        return nil
                    }
                    return SCNVector3(x, y, z)
                }
            return stride(from: 0, to: vertices.count - 2, by: 3).map {
                [vertices[$0], vertices[$0 + 1], vertices[$0 + 2]]
            }
        }
        guard data.count >= 84 else { return [] }
        let triangleCount = Int(data.withUnsafeBytes { $0.load(fromByteOffset: 80, as: UInt32.self) })
        var triangles: [[SCNVector3]] = []
        triangles.reserveCapacity(min(triangleCount, 120_000))
        var offset = 84
        for _ in 0..<min(triangleCount, 120_000) where offset + 50 <= data.count {
            offset += 12
            var triangle: [SCNVector3] = []
            for _ in 0..<3 {
                let x = data.withUnsafeBytes { $0.load(fromByteOffset: offset, as: Float.self) }
                let y = data.withUnsafeBytes { $0.load(fromByteOffset: offset + 4, as: Float.self) }
                let z = data.withUnsafeBytes { $0.load(fromByteOffset: offset + 8, as: Float.self) }
                triangle.append(SCNVector3(x, y, z))
                offset += 12
            }
            triangles.append(triangle)
            offset += 2
        }
        return triangles
    }
}

struct GlossaryView: View {
    private let terms = [
        ("Arch", "One jaw's row of teeth: maxillary (upper) or mandibular (lower)."),
        ("Attachment", "A small composite bump bonded to a tooth so an aligner can grip it. Planning intent only, not a force model."),
        ("Canine", "The pointed corner tooth, position 3 in FDI notation."),
        ("CBCT", "Cone-beam CT. The higher-fidelity record for roots and bone when ordered and interpreted by a professional."),
        ("Coordinate frame", "The axis system movements use. scan-local has z as vertical and x/y in the occlusal plane."),
        ("Crowding", "Too little space, so teeth overlap or twist. The app does not diagnose crowding."),
        ("Cumulative pose", "A tooth's total position after summing every stage up to a selected point."),
        ("Data gap", "A missing record such as roots, CBCT, occlusion, or periodontal status that limits review."),
        ("Extrusion", "Moving a tooth out of the bone, opposite intrusion."),
        ("FDI notation", "Two-digit tooth numbering: first digit is quadrant, second digit counts from the midline."),
        ("Finding", "A structured observation from a deterministic rule or linted advisory review. Never an approval."),
        ("Fixed tooth", "A tooth intended to stay still for part or all of a plan."),
        ("Incisor", "A front cutting tooth, positions 1 and 2."),
        ("Intrusion", "Pushing a tooth into the bone."),
        ("IPR", "Interproximal reduction: planned enamel reduction between adjacent teeth to create space."),
        ("Malocclusion", "A bad bite or misalignment. The app does not diagnose malocclusion."),
        ("Mesh / STL", "A 3D surface model. STL files carry no units, so units start unverified until confirmed."),
        ("Molar", "A large back chewing tooth, positions 6 through 8."),
        ("Movement cap", "A per-stage review threshold for linear, vertical, angular, and rotation movement."),
        ("Occlusion", "How upper and lower teeth meet when biting."),
        ("Premolar", "A tooth between canine and molars, positions 4 and 5."),
        ("Provenance", "Where data came from: patient-derived, imported, manual, model-generated, or synthetic."),
        ("Quadrant", "One of the four mouth sections; the first digit in FDI notation."),
        ("Rotation", "Turning a tooth around its own long axis."),
        ("Segmentation", "Splitting a whole-arch scan into individual per-tooth meshes."),
        ("Spacing", "Unwanted gaps between teeth."),
        ("Stage", "One aligner-style step containing per-tooth movement values."),
        ("Tip", "Mesiodistal angulation: tilting a tooth forward or backward along the arch."),
        ("Torque", "Buccolingual inclination: tilting the crown inward or outward."),
        ("Translation", "Sliding a tooth in millimeters along x, y, or z."),
        ("Units", "The real-world scale of a scan. Must be confirmed before millimeter checks run."),
        ("Wear interval", "How many days each aligner stage is worn; used for projected duration."),
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
    var body: some View {
        List {
            Section("FDI mouth map") {
                ToothMapDiagram()
                    .frame(height: 360)
                    .listRowInsets(EdgeInsets(top: 12, leading: 12, bottom: 12, trailing: 12))
            }
            Section("Quadrants") {
                LabeledContent("Upper right") { Text("18 17 16 15 14 13 12 11") }
                LabeledContent("Upper left") { Text("21 22 23 24 25 26 27 28") }
                LabeledContent("Lower left") { Text("31 32 33 34 35 36 37 38") }
                LabeledContent("Lower right") { Text("48 47 46 45 44 43 42 41") }
            }
        }
        .navigationTitle("Teeth Map")
    }
}

private struct ToothMapDiagram: View {
    private let upperRight = ["18", "17", "16", "15", "14", "13", "12", "11"]
    private let upperLeft = ["21", "22", "23", "24", "25", "26", "27", "28"]
    private let lowerLeft = ["31", "32", "33", "34", "35", "36", "37", "38"]
    private let lowerRight = ["48", "47", "46", "45", "44", "43", "42", "41"]

    var body: some View {
        GeometryReader { proxy in
            let size = proxy.size
            let centerX = size.width / 2
            let centerY = size.height / 2
            let radiusX = min(size.width * 0.43, 172)
            let upperY = centerY - 68
            let lowerY = centerY + 68
            let mouthRect = CGRect(x: 16, y: 24, width: size.width - 32, height: size.height - 48)

            ZStack {
                RoundedRectangle(cornerRadius: 18)
                    .fill(Color(.secondarySystemGroupedBackground))
                Canvas { context, _ in
                    let mouth = Path(ellipseIn: mouthRect)
                    context.fill(mouth, with: .color(.pink.opacity(0.16)))
                    context.stroke(mouth, with: .color(.pink.opacity(0.38)), lineWidth: 3)

                    let palate = Path(ellipseIn: CGRect(x: centerX - 70, y: centerY - 82, width: 140, height: 104))
                    context.fill(palate, with: .color(.pink.opacity(0.18)))

                    let tongue = Path(ellipseIn: CGRect(x: centerX - 78, y: centerY + 20, width: 156, height: 118))
                    context.fill(tongue, with: .color(.red.opacity(0.12)))

                    var upperArch = Path()
                    upperArch.addArc(
                        center: CGPoint(x: centerX, y: upperY + 86),
                        radius: radiusX,
                        startAngle: .degrees(202),
                        endAngle: .degrees(338),
                        clockwise: false
                    )
                    context.stroke(upperArch, with: .color(.pink.opacity(0.48)), lineWidth: 34)

                    var lowerArch = Path()
                    lowerArch.addArc(
                        center: CGPoint(x: centerX, y: lowerY - 86),
                        radius: radiusX,
                        startAngle: .degrees(22),
                        endAngle: .degrees(158),
                        clockwise: false
                    )
                    context.stroke(lowerArch, with: .color(.pink.opacity(0.48)), lineWidth: 34)

                    var occlusalGap = Path()
                    occlusalGap.move(to: CGPoint(x: centerX - radiusX + 12, y: centerY))
                    occlusalGap.addCurve(
                        to: CGPoint(x: centerX + radiusX - 12, y: centerY),
                        control1: CGPoint(x: centerX - 72, y: centerY + 18),
                        control2: CGPoint(x: centerX + 72, y: centerY + 18)
                    )
                    context.stroke(occlusalGap, with: .color(.secondary.opacity(0.24)), lineWidth: 2)

                    var midline = Path()
                    midline.move(to: CGPoint(x: centerX, y: 42))
                    midline.addLine(to: CGPoint(x: centerX, y: size.height - 42))
                    context.stroke(midline, with: .color(.secondary.opacity(0.32)), lineWidth: 1)
                }
                Text("Upper")
                    .font(.caption.bold())
                    .foregroundStyle(.secondary)
                    .position(x: centerX, y: 36)
                Text("Lower")
                    .font(.caption.bold())
                    .foregroundStyle(.secondary)
                    .position(x: centerX, y: size.height - 34)
                Text("Patient right")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .position(x: 70, y: centerY)
                Text("Patient left")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .position(x: size.width - 70, y: centerY)

                ForEach(Array(upperRight.enumerated()), id: \.element) { offset, label in
                    ToothBadge(label: label, point: upperPoint(index: offset, side: -1, centerX: centerX, y: upperY, radiusX: radiusX), kind: toothKind(index: offset), isUpper: true)
                }
                ForEach(Array(upperLeft.enumerated()), id: \.element) { offset, label in
                    ToothBadge(label: label, point: upperPoint(index: offset, side: 1, centerX: centerX, y: upperY, radiusX: radiusX), kind: toothKind(index: offset), isUpper: true)
                }
                ForEach(Array(lowerLeft.enumerated()), id: \.element) { offset, label in
                    ToothBadge(label: label, point: lowerPoint(index: offset, side: 1, centerX: centerX, y: lowerY, radiusX: radiusX), kind: toothKind(index: offset), isUpper: false)
                }
                ForEach(Array(lowerRight.enumerated()), id: \.element) { offset, label in
                    ToothBadge(label: label, point: lowerPoint(index: offset, side: -1, centerX: centerX, y: lowerY, radiusX: radiusX), kind: toothKind(index: offset), isUpper: false)
                }
            }
            .accessibilityLabel("FDI teeth map drawn as an open mouth with upper and lower dental arches")
        }
    }

    private func upperPoint(index: Int, side: CGFloat, centerX: CGFloat, y: CGFloat, radiusX: CGFloat) -> CGPoint {
        let t = CGFloat(index) / 7
        let distance = 16 + t * (radiusX - 34)
        let archLift = sin(t * .pi) * 66
        return CGPoint(x: centerX + side * distance, y: y + archLift)
    }

    private func lowerPoint(index: Int, side: CGFloat, centerX: CGFloat, y: CGFloat, radiusX: CGFloat) -> CGPoint {
        let t = CGFloat(index) / 7
        let distance = 16 + t * (radiusX - 34)
        let archDrop = sin(t * .pi) * 66
        return CGPoint(x: centerX + side * distance, y: y - archDrop)
    }

    private func toothKind(index: Int) -> ToothKind {
        switch index {
        case 0, 1: return .molar
        case 2, 3: return .premolar
        case 4: return .canine
        default: return .incisor
        }
    }
}

private enum ToothKind {
    case incisor
    case canine
    case premolar
    case molar
}

private struct ToothBadge: View {
    var label: String
    var point: CGPoint
    var kind: ToothKind
    var isUpper: Bool

    var body: some View {
        ZStack {
            ToothShape(kind: kind, isUpper: isUpper)
                .fill(Color(.systemBackground))
                .shadow(color: .black.opacity(0.14), radius: 2, y: 1)
                .overlay {
                    ToothShape(kind: kind, isUpper: isUpper)
                        .stroke(Color(.separator).opacity(0.7), lineWidth: 1)
                }
            Text(label)
                .font(.caption2.bold())
                .monospacedDigit()
                .foregroundStyle(.primary)
                .padding(.top, kind == .canine && !isUpper ? 3 : 0)
                .padding(.bottom, kind == .canine && isUpper ? 3 : 0)
        }
        .frame(width: toothSize.width, height: toothSize.height)
        .position(point)
    }

    private var toothSize: CGSize {
        switch kind {
        case .incisor: return CGSize(width: 34, height: 42)
        case .canine: return CGSize(width: 36, height: 46)
        case .premolar: return CGSize(width: 42, height: 40)
        case .molar: return CGSize(width: 48, height: 42)
        }
    }
}

private struct ToothShape: Shape {
    var kind: ToothKind
    var isUpper: Bool

    func path(in rect: CGRect) -> Path {
        var path = Path()
        switch kind {
        case .canine:
            if isUpper {
                path.move(to: CGPoint(x: rect.midX, y: rect.maxY))
                path.addCurve(to: CGPoint(x: rect.minX + 4, y: rect.midY), control1: CGPoint(x: rect.midX - 10, y: rect.maxY - 4), control2: CGPoint(x: rect.minX + 4, y: rect.midY + 10))
                path.addCurve(to: CGPoint(x: rect.midX, y: rect.minY), control1: CGPoint(x: rect.minX + 4, y: rect.minY + 8), control2: CGPoint(x: rect.midX - 10, y: rect.minY))
                path.addCurve(to: CGPoint(x: rect.maxX - 4, y: rect.midY), control1: CGPoint(x: rect.midX + 10, y: rect.minY), control2: CGPoint(x: rect.maxX - 4, y: rect.minY + 8))
                path.addCurve(to: CGPoint(x: rect.midX, y: rect.maxY), control1: CGPoint(x: rect.maxX - 4, y: rect.midY + 10), control2: CGPoint(x: rect.midX + 10, y: rect.maxY - 4))
            } else {
                path.move(to: CGPoint(x: rect.midX, y: rect.minY))
                path.addCurve(to: CGPoint(x: rect.minX + 4, y: rect.midY), control1: CGPoint(x: rect.midX - 10, y: rect.minY + 4), control2: CGPoint(x: rect.minX + 4, y: rect.midY - 10))
                path.addCurve(to: CGPoint(x: rect.midX, y: rect.maxY), control1: CGPoint(x: rect.minX + 4, y: rect.maxY - 8), control2: CGPoint(x: rect.midX - 10, y: rect.maxY))
                path.addCurve(to: CGPoint(x: rect.maxX - 4, y: rect.midY), control1: CGPoint(x: rect.midX + 10, y: rect.maxY), control2: CGPoint(x: rect.maxX - 4, y: rect.maxY - 8))
                path.addCurve(to: CGPoint(x: rect.midX, y: rect.minY), control1: CGPoint(x: rect.maxX - 4, y: rect.midY - 10), control2: CGPoint(x: rect.midX + 10, y: rect.minY + 4))
            }
        default:
            let radius: CGFloat = kind == .molar ? 14 : 11
            path.addRoundedRect(in: rect.insetBy(dx: 1, dy: 1), cornerSize: CGSize(width: radius, height: radius))
        }
        return path
    }
}
