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
    @State private var selectedImport: ImporterKind = .stl
    @State private var photoItems: [PhotosPickerItem] = []

    private enum ImporterKind: Identifiable {
        case stl, cbct, photoFiles, browserReview

        var id: String { modality }

        var title: String {
            switch self {
            case .stl: return "STL scans"
            case .cbct: return "CBCT / DICOM"
            case .photoFiles: return "Photos"
            case .browserReview: return "Browser review"
            }
        }

        var subtitle: String {
            switch self {
            case .stl: return "3D surface files"
            case .cbct: return "Attach for handoff"
            case .photoFiles: return "Library or files"
            case .browserReview: return "Case JSON"
            }
        }

        var actionTitle: String {
            switch self {
            case .stl: return "Choose STL scans"
            case .cbct: return "Choose CBCT / DICOM"
            case .photoFiles: return "Choose photos"
            case .browserReview: return "Import review JSON"
            }
        }

        var systemImage: String {
            switch self {
            case .stl: return "cube.transparent"
            case .cbct: return "waveform.path.ecg.rectangle"
            case .photoFiles: return "photo"
            case .browserReview: return "doc.text"
            }
        }

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
            VStack(alignment: .leading, spacing: 12) {
                Text("Choose what to add")
                    .font(.headline)
                LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                    ForEach([ImporterKind.stl, .cbct, .photoFiles, .browserReview]) { option in
                        ImportOptionCard(
                            title: option.title,
                            subtitle: option.subtitle,
                            systemImage: option.systemImage,
                            isSelected: selectedImport == option
                        ) {
                            selectedImport = option
                        }
                    }
                }
                if selectedImport == .photoFiles {
                    PhotosPicker(selection: $photoItems, maxSelectionCount: 12, matching: .images) {
                        Label("Add photos from library", systemImage: "photo.on.rectangle")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                    Button {
                        importer = .photoFiles
                    } label: {
                        Label("Browse Files or Drive", systemImage: "folder")
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.bordered)
                } else {
                    Button {
                        importer = selectedImport
                    } label: {
                        Label(selectedImport.actionTitle, systemImage: selectedImport.systemImage)
                            .frame(maxWidth: .infinity)
                    }
                    .buttonStyle(.borderedProminent)
                }
            }
            .padding(12)
            .background(.thinMaterial)
            .clipShape(RoundedRectangle(cornerRadius: 12))
            if !model.storedReviews.isEmpty {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Stored browser reviews")
                        .font(.headline)
                    ForEach(model.storedReviews) { review in
                        VStack(alignment: .leading, spacing: 2) {
                            Text(review.fileName).font(.caption.bold())
                            if let caseReview = review.caseReview {
                                Text(caseReview.mobileSummary)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            } else {
                                Text("\(review.byteCount) bytes")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
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

private struct ImportOptionCard: View {
    var title: String
    var subtitle: String
    var systemImage: String
    var isSelected: Bool
    var action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(alignment: .leading, spacing: 6) {
                Image(systemName: systemImage)
                    .font(.title3)
                Text(title)
                    .font(.subheadline.bold())
                Text(subtitle)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(10)
            .background(isSelected ? Color.accentColor.opacity(0.12) : Color(.secondarySystemGroupedBackground))
            .overlay {
                RoundedRectangle(cornerRadius: 10)
                    .stroke(isSelected ? Color.accentColor : Color(.separator), lineWidth: isSelected ? 2 : 1)
            }
            .clipShape(RoundedRectangle(cornerRadius: 10))
        }
        .buttonStyle(.plain)
    }
}

/// Step 2: staged teeth preview and timeline controls.
struct TeethAndTimeView: View {
    @EnvironmentObject private var model: LiteFlowViewModel
    @State private var stage = 0.0
    @State private var showDemoSample = false
    @State private var previewArch: DentalPreviewArch = .both
    @State private var zoom = 1.0

    private var hasSelectedStl: Bool {
        model.scans.contains { $0.modality.lowercased() == "stl" }
    }

    var body: some View {
        VStack(spacing: 16) {
            Text("Teeth + time")
                .font(.title3.bold())
            DentalScenePreview(
                stage: stage,
                scans: model.previewScans,
                previewArch: previewArch,
                zoom: zoom,
                hasSelectedStl: hasSelectedStl
            )
                .frame(height: 340)
                .clipShape(RoundedRectangle(cornerRadius: 12))
            if hasSelectedStl {
                Picker("Arch", selection: $previewArch) {
                    ForEach(DentalPreviewArch.allCases, id: \.self) { arch in
                        Text(arch.title).tag(arch)
                    }
                }
                .pickerStyle(.segmented)
                HStack(spacing: 12) {
                    Text("Zoom")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Slider(value: $zoom, in: 0.75...2.4, step: 0.05)
                    Text(String(format: "%.1fx", zoom))
                        .font(.caption.monospacedDigit())
                        .foregroundStyle(.secondary)
                        .frame(width: 42, alignment: .trailing)
                }
            }
            if !hasSelectedStl {
                VStack(spacing: 8) {
                    Button {
                        withAnimation(.snappy) {
                            showDemoSample.toggle()
                        }
                    } label: {
                        Label("Demo sample", systemImage: showDemoSample ? "chevron.up.circle" : "chevron.down.circle")
                    }
                    .buttonStyle(.bordered)
                    if showDemoSample {
                        Button {
                            model.addDevSampleSTL()
                            withAnimation(.snappy) {
                                showDemoSample = false
                            }
                        } label: {
                            Label("Use full-arch dev sample", systemImage: "cube.transparent")
                        }
                        .buttonStyle(.borderedProminent)
                        Text("Loads bundled upper and lower STL scans for a full mobile rendering preview.")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                }
                .frame(maxWidth: .infinity)
            }
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
                            if let caseReview = review.caseReview {
                                Text(caseReview.reviewTier.label)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                Text("\(caseReview.unresolvedDataGaps.count) unresolved data gaps. Mobile edit lock: \(caseReview.editable.requiresBrowserEngine ? "browser engine required" : "unknown").")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                if let openURL = caseReview.handoff.openURL {
                                    Link("Open browser case", destination: openURL)
                                        .font(.caption)
                                }
                                if let deepLink = caseReview.handoff.deepLinkURL {
                                    Link("Open app link", destination: deepLink)
                                        .font(.caption)
                                }
                            } else {
                                Text("\(review.byteCount) bytes stored on this device for review/sharing. Open the browser workspace to edit the source plan.")
                                    .font(.caption).foregroundStyle(.secondary)
                            }
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
    @State private var packageStatus = "Preparing package..."

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
            Text(packageStatus)
                .font(.caption)
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
                Button {
                    preparePackage()
                } label: {
                    Label("Refresh package", systemImage: "arrow.clockwise")
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
            if let packageURL {
                let bytes = ((try? packageURL.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0)
                packageStatus = "Package ready: \(packageURL.lastPathComponent) · \(ByteCountFormatter.string(fromByteCount: Int64(bytes), countStyle: .file))"
            }
        } catch {
            exportError = "Could not prepare export package: \(error.localizedDescription)"
            packageURL = nil
            packageStatus = "Package is not ready."
        }
    }
}

struct DentalScenePreview: View {
    var stage: Double
    var scans: [PreviewScan]
    var previewArch: DentalPreviewArch = .both
    var zoom: Double = 1
    var hasSelectedStl: Bool = false

    var body: some View {
        ZStack(alignment: .bottomLeading) {
            SceneView(
                scene: DentalPreviewScene.make(stage: stage, scans: scans, previewArch: previewArch, zoom: zoom),
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
        if hasSelectedStl {
            return "Showing sample teeth preview"
        }
        if scans.contains(where: { $0.modality.lowercased() == "cbct" }) {
            return "CBCT attached; open browser/full engine for volume rendering"
        }
        return "Add an STL scan to render patient geometry"
    }
}

enum DentalPreviewArch: CaseIterable {
    case both
    case upper
    case lower

    var title: String {
        switch self {
        case .both: return "Both"
        case .upper: return "Upper"
        case .lower: return "Lower"
        }
    }

    func includes(_ scan: PreviewScan) -> Bool {
        guard scan.modality.lowercased() == "stl" else { return false }
        let name = scan.fileName.lowercased()
        switch self {
        case .both:
            return true
        case .upper:
            return name.contains("upper") || name.contains("maxillary")
        case .lower:
            return name.contains("lower") || name.contains("mandibular")
        }
    }
}

private enum DentalPreviewScene {
    static func make(stage: Double, scans: [PreviewScan], previewArch: DentalPreviewArch, zoom: Double) -> SCNScene {
        let scene = SCNScene()
        scene.background.contents = UIColor.systemBackground

        let camera = SCNCamera()
        camera.fieldOfView = 36
        let cameraNode = SCNNode()
        cameraNode.camera = camera
        cameraNode.position = SCNVector3(0, 0, Float(7.2 / Swift.max(0.75, zoom)))
        scene.rootNode.addChildNode(cameraNode)

        let ambient = SCNLight()
        ambient.type = .ambient
        ambient.intensity = 560
        let ambientNode = SCNNode()
        ambientNode.light = ambient
        scene.rootNode.addChildNode(ambientNode)

        let light = SCNLight()
        light.type = .directional
        light.intensity = 1_350
        let lightNode = SCNNode()
        lightNode.light = light
        lightNode.eulerAngles = SCNVector3(-0.6, 0.25, 0)
        lightNode.position = SCNVector3(0, 4, 6)
        scene.rootNode.addChildNode(lightNode)

        let selectedScans = selectedScans(from: scans, previewArch: previewArch)
        let stlNodes = selectedScans.compactMap(STLSceneMesh.node)
        if stlNodes.isEmpty {
            addSampleDentalCast(to: scene, stage: stage)
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

    private static func selectedScans(from scans: [PreviewScan], previewArch: DentalPreviewArch) -> [PreviewScan] {
        let stlScans = Array(scans.filter { $0.modality.lowercased() == "stl" }.prefix(2))
        guard previewArch != .both else { return stlScans }

        let namedMatches = stlScans.filter(previewArch.includes)
        if !namedMatches.isEmpty {
            return namedMatches
        }
        guard stlScans.count > 1 else { return stlScans }
        return previewArch == .upper ? [stlScans[0]] : [stlScans[1]]
    }

    private static func centerAndScale(_ node: SCNNode) {
        guard let bounds = recursiveBounds(for: node) else { return }
        let min = bounds.min
        let maxPoint = bounds.max
        let center = SCNVector3((min.x + maxPoint.x) / 2, (min.y + maxPoint.y) / 2, (min.z + maxPoint.z) / 2)
        let span = Swift.max(maxPoint.x - min.x, Swift.max(maxPoint.y - min.y, maxPoint.z - min.z))
        let scale = span > 0 ? 6.2 / span : 1
        for child in node.childNodes {
            child.position = SCNVector3(
                child.position.x - center.x,
                child.position.y - center.y,
                child.position.z - center.z
            )
        }
        node.position = SCNVector3Zero
        node.scale = SCNVector3(scale, scale, scale)
        node.eulerAngles.x = -.pi / 2
    }

    private static func recursiveBounds(for node: SCNNode) -> (min: SCNVector3, max: SCNVector3)? {
        var result: (min: SCNVector3, max: SCNVector3)?
        for child in node.childNodes {
            let bounds = child.boundingBox
            let corners = [
                SCNVector3(bounds.min.x, bounds.min.y, bounds.min.z),
                SCNVector3(bounds.min.x, bounds.min.y, bounds.max.z),
                SCNVector3(bounds.min.x, bounds.max.y, bounds.min.z),
                SCNVector3(bounds.min.x, bounds.max.y, bounds.max.z),
                SCNVector3(bounds.max.x, bounds.min.y, bounds.min.z),
                SCNVector3(bounds.max.x, bounds.min.y, bounds.max.z),
                SCNVector3(bounds.max.x, bounds.max.y, bounds.min.z),
                SCNVector3(bounds.max.x, bounds.max.y, bounds.max.z),
            ]
            for corner in corners {
                let converted = child.convertPosition(corner, to: node)
                if let current = result {
                    result = (
                        min: SCNVector3(Swift.min(current.min.x, converted.x), Swift.min(current.min.y, converted.y), Swift.min(current.min.z, converted.z)),
                        max: SCNVector3(Swift.max(current.max.x, converted.x), Swift.max(current.max.y, converted.y), Swift.max(current.max.z, converted.z))
                    )
                } else {
                    result = (converted, converted)
                }
            }
        }
        return result
    }

    private static func addSampleDentalCast(to scene: SCNScene, stage: Double) {
        let parent = SCNNode()
        parent.eulerAngles.x = -0.08
        parent.eulerAngles.y = 0.12
        scene.rootNode.addChildNode(parent)

        addScanBase(to: parent, y: 0.76, isUpper: true)
        addScanBase(to: parent, y: -0.72, isUpper: false)
        addArch(to: parent, y: 0.28, stage: stage, isUpper: true)
        addArch(to: parent, y: -0.28, stage: stage, isUpper: false)

        let grid = SCNPlane(width: 7.2, height: 3.2)
        grid.firstMaterial?.diffuse.contents = UIColor.systemGray5
        let gridNode = SCNNode(geometry: grid)
        gridNode.position = SCNVector3(0, -1.72, -0.92)
        gridNode.eulerAngles.x = -.pi / 2
        scene.rootNode.addChildNode(gridNode)
    }

    private static func addScanBase(to parent: SCNNode, y: Float, isUpper: Bool) {
        let base = SCNBox(width: 5.4, height: 0.52, length: 1.2, chamferRadius: 0.18)
        base.firstMaterial?.diffuse.contents = UIColor(red: 0.77, green: 0.75, blue: 0.66, alpha: 1)
        base.firstMaterial?.specular.contents = UIColor.white
        let baseNode = SCNNode(geometry: base)
        baseNode.position = SCNVector3(0, y, -0.32)
        baseNode.scale.y = isUpper ? 0.72 : 0.64
        parent.addChildNode(baseNode)

        for index in 0..<11 {
            let centered = Float(index) - 5
            let ridge = SCNSphere(radius: 0.16 + CGFloat(abs(centered)) * 0.006)
            ridge.segmentCount = 12
            ridge.firstMaterial?.diffuse.contents = UIColor(red: 0.82, green: 0.80, blue: 0.72, alpha: 1)
            let ridgeNode = SCNNode(geometry: ridge)
            ridgeNode.scale = SCNVector3(1.8, isUpper ? 0.54 : 0.48, 0.34)
            ridgeNode.position = SCNVector3(centered * 0.5, y + (isUpper ? -0.08 : 0.08), -0.14 - abs(centered) * 0.012)
            parent.addChildNode(ridgeNode)
        }
    }

    private static func addArch(to parent: SCNNode, y: Float, stage: Double, isUpper: Bool) {
        let progress = Float(stage / 12.0)
        for index in 0..<16 {
            let centered = Float(index) - 7.5
            let normalized = abs(centered) / 6.5
            let crown = sampleToothGeometry(index: index)
            crown.firstMaterial?.diffuse.contents = UIColor(red: 0.91, green: 0.89, blue: 0.80, alpha: 1)
            crown.firstMaterial?.specular.contents = UIColor.white

            let node = SCNNode(geometry: crown)
            let archDepth = (1 - min(normalized, 1) * min(normalized, 1)) * 0.36
            let lateralExpansion = (centered >= 0 ? 1 : -1) * progress * 0.14
            node.position = SCNVector3(
                centered * 0.3 + lateralExpansion,
                y + archDepth * (isUpper ? 1 : -1),
                0.14 - normalized * 0.08
            )
            node.eulerAngles.z = -centered * 0.035
            node.eulerAngles.x = isUpper ? 0.02 : -0.02
            node.scale = SCNVector3(1.0 + normalized * 0.22, isUpper ? 1.04 : 0.98, 0.82 + normalized * 0.14)
            parent.addChildNode(node)
        }
    }

    private static func sampleToothGeometry(index: Int) -> SCNGeometry {
        let distanceFromMidline = abs(index - 7)
        if distanceFromMidline <= 1 {
            return SCNBox(width: 0.34, height: 0.74, length: 0.34, chamferRadius: 0.1)
        }
        if distanceFromMidline == 2 {
            return SCNPyramid(width: 0.4, height: 0.78, length: 0.4)
        }
        if distanceFromMidline <= 4 {
            return SCNBox(width: 0.42, height: 0.58, length: 0.44, chamferRadius: 0.12)
        }
        return SCNBox(width: 0.52, height: 0.48, length: 0.52, chamferRadius: 0.13)
    }
}

private enum STLSceneMesh {
    private static let trianglePreviewLimit = 120_000
    private static var geometryCache: [String: SCNGeometry] = [:]
    private static let cacheLock = NSLock()

    static func node(from scan: PreviewScan) -> SCNNode? {
        let cacheKey = "\(scan.fileName):\(scan.data.count)"
        if let cached = cachedGeometry(for: cacheKey) {
            return SCNNode(geometry: cached)
        }

        let triangles = parseTriangles(from: scan.data)
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
        let material = SCNMaterial()
        material.diffuse.contents = UIColor(red: 0.99, green: 0.96, blue: 0.82, alpha: 1.0)
        material.ambient.contents = UIColor(red: 0.62, green: 0.56, blue: 0.36, alpha: 1.0)
        material.specular.contents = UIColor(white: 0.9, alpha: 1.0)
        material.emission.contents = UIColor(red: 0.06, green: 0.05, blue: 0.02, alpha: 1.0)
        material.shininess = 0.45
        material.lightingModel = .blinn
        material.isDoubleSided = true
        geometry.materials = [material]
        storeGeometry(geometry, for: cacheKey)
        return SCNNode(geometry: geometry)
    }

    private static func cachedGeometry(for key: String) -> SCNGeometry? {
        cacheLock.lock()
        defer { cacheLock.unlock() }
        return geometryCache[key]
    }

    private static func storeGeometry(_ geometry: SCNGeometry, for key: String) {
        cacheLock.lock()
        geometryCache[key] = geometry
        cacheLock.unlock()
    }

    private static func parseTriangles(from data: Data) -> [[SCNVector3]] {
        if let ascii = String(data: data.prefix(4 * 1024 * 1024), encoding: .utf8), ascii.contains("vertex") {
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
        guard data.count >= 84, let rawTriangleCount = littleEndianUInt32(in: data, at: 80) else { return [] }
        let triangleCount = Int(rawTriangleCount)
        var triangles: [[SCNVector3]] = []
        triangles.reserveCapacity(min(triangleCount, trianglePreviewLimit))
        let sampleStep = Swift.max(1, triangleCount / trianglePreviewLimit)
        var triangleIndex = 0
        while triangleIndex < triangleCount && triangles.count < trianglePreviewLimit {
            var offset = 84 + triangleIndex * 50 + 12
            guard offset + 36 <= data.count else { break }
            var triangle: [SCNVector3] = []
            for _ in 0..<3 {
                guard let x = littleEndianFloat(in: data, at: offset),
                      let y = littleEndianFloat(in: data, at: offset + 4),
                      let z = littleEndianFloat(in: data, at: offset + 8) else {
                    break
                }
                triangle.append(SCNVector3(x, y, z))
                offset += 12
            }
            if triangle.count == 3 {
                triangles.append(triangle)
            }
            triangleIndex += sampleStep
        }
        return triangles
    }

    private static func littleEndianFloat(in data: Data, at offset: Int) -> Float? {
        littleEndianUInt32(in: data, at: offset).map { Float(bitPattern: $0) }
    }

    private static func littleEndianUInt32(in data: Data, at offset: Int) -> UInt32? {
        guard offset >= 0, offset + 4 <= data.count else { return nil }
        return UInt32(data[offset])
            | UInt32(data[offset + 1]) << 8
            | UInt32(data[offset + 2]) << 16
            | UInt32(data[offset + 3]) << 24
    }
}

struct GlossaryView: View {
    @State private var query = ""
    // BEGIN GENERATED GLOSSARY TERMS
    private let terms = [
        ("Arch", "One jaw's row of teeth: maxillary (upper) or mandibular (lower)."),
        ("Attachment", "A small composite bump bonded to a tooth so an aligner can grip it. Planning intent only, not a force model."),
        ("Canine", "The pointed corner tooth, position 3 in FDI notation."),
        ("CBCT", "Cone-beam CT. The higher-fidelity record for roots and bone when ordered and interpreted by a professional."),
        ("Class I bite", "A common reference bite where the upper and lower first molars fit in the expected front/back relationship. It can still have crowding, spacing, or other issues; the app does not diagnose bite class."),
        ("Class II bite", "A front/back bite pattern where the lower teeth or jaw sit farther back relative to the upper teeth than in Class I. The app can record geometry, but it does not diagnose or correct this relationship."),
        ("Class III bite", "A front/back bite pattern where the lower teeth or jaw sit farther forward relative to the upper teeth than in Class I. The app can visualize scans, but it does not diagnose jaw relationships."),
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
        ("Malocclusion", "A bad bite or misalignment. Class I, II, and III are broad bite-relationship categories, not treatment instructions. The app does not diagnose malocclusion."),
        ("Mesh / STL", "A 3D surface model. STL stands for stereolithography; STL files describe triangle surfaces and carry no units, so units start unverified until confirmed."),
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
    // END GENERATED GLOSSARY TERMS

    var body: some View {
        List {
            ForEach(groupedTerms, id: \.letter) { group in
                Section(group.letter) {
                    ForEach(group.items, id: \.0) { term, definition in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(term).font(.headline)
                            Text(definition).font(.subheadline).foregroundStyle(.secondary)
                        }
                    }
                }
            }
        }
        .searchable(text: $query, placement: .navigationBarDrawer(displayMode: .always), prompt: "Search glossary")
        .navigationTitle("Glossary")
    }

    private var filteredTerms: [(String, String)] {
        let needle = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        guard !needle.isEmpty else { return terms }
        return terms.filter { term, definition in
            term.lowercased().contains(needle) || definition.lowercased().contains(needle)
        }
    }

    private var groupedTerms: [(letter: String, items: [(String, String)])] {
        let grouped = Dictionary(grouping: filteredTerms) { item in
            String(item.0.prefix(1)).uppercased()
        }
        return grouped.keys.sorted().map { letter in
            (letter, grouped[letter, default: []].sorted { $0.0 < $1.0 })
        }
    }
}

struct TeethMapView: View {
    @State private var numberingSystem: ToothNumberingSystem = .fdi

    var body: some View {
        List {
            Section {
                Picker("Numbering", selection: $numberingSystem) {
                    ForEach(ToothNumberingSystem.allCases, id: \.self) { system in
                        Text(system.shortTitle).tag(system)
                    }
                }
                .pickerStyle(.segmented)

                Text(numberingSystem.description)
                    .font(.caption)
                    .foregroundStyle(.secondary)

                ToothMapDiagram(numberingSystem: numberingSystem)
                    .frame(height: 390)
                    .listRowInsets(EdgeInsets(top: 12, leading: 12, bottom: 12, trailing: 12))
            } header: {
                Text(numberingSystem.sectionTitle)
            }
            Section("Quadrants") {
                LabeledContent("Upper right") { Text(numberingSystem.upperRight.joined(separator: " ")) }
                LabeledContent("Upper left") { Text(numberingSystem.upperLeft.joined(separator: " ")) }
                LabeledContent("Lower left") { Text(numberingSystem.lowerLeft.joined(separator: " ")) }
                LabeledContent("Lower right") { Text(numberingSystem.lowerRight.joined(separator: " ")) }
            }
        }
        .navigationTitle("Teeth Map")
    }
}

private enum ToothNumberingSystem: CaseIterable {
    case fdi
    case universal

    var shortTitle: String {
        switch self {
        case .fdi: return "FDI"
        case .universal: return "Universal"
        }
    }

    var sectionTitle: String {
        switch self {
        case .fdi: return "Federation Dentaire Internationale (FDI) mouth map"
        case .universal: return "Universal numbering mouth map"
        }
    }

    var description: String {
        switch self {
        case .fdi:
            return "Federation Dentaire Internationale (FDI) uses a two-digit number: quadrant first, then tooth position from the midline."
        case .universal:
            return "Universal numbering labels permanent teeth 1 through 32, starting at the upper right third molar."
        }
    }

    var upperRight: [String] {
        switch self {
        case .fdi: return ["18", "17", "16", "15", "14", "13", "12", "11"]
        case .universal: return ["1", "2", "3", "4", "5", "6", "7", "8"]
        }
    }

    var upperLeft: [String] {
        switch self {
        case .fdi: return ["21", "22", "23", "24", "25", "26", "27", "28"]
        case .universal: return ["9", "10", "11", "12", "13", "14", "15", "16"]
        }
    }

    var lowerLeft: [String] {
        switch self {
        case .fdi: return ["31", "32", "33", "34", "35", "36", "37", "38"]
        case .universal: return ["24", "23", "22", "21", "20", "19", "18", "17"]
        }
    }

    var lowerRight: [String] {
        switch self {
        case .fdi: return ["48", "47", "46", "45", "44", "43", "42", "41"]
        case .universal: return ["32", "31", "30", "29", "28", "27", "26", "25"]
        }
    }
}

private struct ToothMapDiagram: View {
    var numberingSystem: ToothNumberingSystem

    var body: some View {
        GeometryReader { proxy in
            let size = proxy.size
            let centerX = size.width / 2
            let centerY = size.height / 2
            let radiusX = min(size.width * 0.37, 132)
            let upperY = centerY - 104
            let lowerY = centerY + 104

            ZStack {
                RoundedRectangle(cornerRadius: 18)
                    .fill(Color(.secondarySystemGroupedBackground))
                Canvas { context, _ in
                    let upperGum = gumPath(centerX: centerX, baseY: upperY, radiusX: radiusX, upper: true)
                    let lowerGum = gumPath(centerX: centerX, baseY: lowerY, radiusX: radiusX, upper: false)
                    context.stroke(upperGum, with: .color(.pink.opacity(0.34)), lineWidth: 28)
                    context.stroke(lowerGum, with: .color(.pink.opacity(0.34)), lineWidth: 28)

                    let palate = Path(ellipseIn: CGRect(x: centerX - 74, y: upperY + 14, width: 148, height: 74))
                    context.fill(palate, with: .color(.pink.opacity(0.12)))

                    let tongue = Path(ellipseIn: CGRect(x: centerX - 80, y: lowerY - 88, width: 160, height: 82))
                    context.fill(tongue, with: .color(.red.opacity(0.08)))

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
                    .position(x: 68, y: centerY)
                Text("Patient left")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
                    .position(x: size.width - 70, y: centerY)

                ForEach(teeth(for: .upperRight), id: \.fdi) { tooth in
                    NumberedToothBadge(tooth: tooth, point: toothPoint(label: tooth.fdi, centerX: centerX, upperY: upperY, lowerY: lowerY, radiusX: radiusX), labelPoint: labelPoint(label: tooth.fdi, centerX: centerX, upperY: upperY, lowerY: lowerY, radiusX: radiusX), numberingSystem: numberingSystem, kind: toothKind(label: tooth.fdi), isUpper: true)
                }
                ForEach(teeth(for: .upperLeft), id: \.fdi) { tooth in
                    NumberedToothBadge(tooth: tooth, point: toothPoint(label: tooth.fdi, centerX: centerX, upperY: upperY, lowerY: lowerY, radiusX: radiusX), labelPoint: labelPoint(label: tooth.fdi, centerX: centerX, upperY: upperY, lowerY: lowerY, radiusX: radiusX), numberingSystem: numberingSystem, kind: toothKind(label: tooth.fdi), isUpper: true)
                }
                ForEach(teeth(for: .lowerLeft), id: \.fdi) { tooth in
                    NumberedToothBadge(tooth: tooth, point: toothPoint(label: tooth.fdi, centerX: centerX, upperY: upperY, lowerY: lowerY, radiusX: radiusX), labelPoint: labelPoint(label: tooth.fdi, centerX: centerX, upperY: upperY, lowerY: lowerY, radiusX: radiusX), numberingSystem: numberingSystem, kind: toothKind(label: tooth.fdi), isUpper: false)
                }
                ForEach(teeth(for: .lowerRight), id: \.fdi) { tooth in
                    NumberedToothBadge(tooth: tooth, point: toothPoint(label: tooth.fdi, centerX: centerX, upperY: upperY, lowerY: lowerY, radiusX: radiusX), labelPoint: labelPoint(label: tooth.fdi, centerX: centerX, upperY: upperY, lowerY: lowerY, radiusX: radiusX), numberingSystem: numberingSystem, kind: toothKind(label: tooth.fdi), isUpper: false)
                }
            }
            .accessibilityLabel("\(numberingSystem.sectionTitle) drawn as an open mouth with upper and lower dental arches")
        }
    }

    private enum Quadrant {
        case upperRight
        case upperLeft
        case lowerLeft
        case lowerRight
    }

    struct ToothNumber {
        let fdi: String
        let universal: String

        func label(for numberingSystem: ToothNumberingSystem) -> String {
            numberingSystem == .fdi ? fdi : universal
        }
    }

    private func teeth(for quadrant: Quadrant) -> [ToothNumber] {
        switch quadrant {
        case .upperRight:
            return zip(["18", "17", "16", "15", "14", "13", "12", "11"], ["1", "2", "3", "4", "5", "6", "7", "8"]).map(ToothNumber.init)
        case .upperLeft:
            return zip(["21", "22", "23", "24", "25", "26", "27", "28"], ["9", "10", "11", "12", "13", "14", "15", "16"]).map(ToothNumber.init)
        case .lowerLeft:
            return zip(["31", "32", "33", "34", "35", "36", "37", "38"], ["24", "23", "22", "21", "20", "19", "18", "17"]).map(ToothNumber.init)
        case .lowerRight:
            return zip(["48", "47", "46", "45", "44", "43", "42", "41"], ["32", "31", "30", "29", "28", "27", "26", "25"]).map(ToothNumber.init)
        }
    }

    private func gumPath(centerX: CGFloat, baseY: CGFloat, radiusX: CGFloat, upper: Bool) -> Path {
        var path = Path()
        path.move(to: CGPoint(x: centerX - radiusX, y: baseY + (upper ? 96 : -96)))
        path.addCurve(
            to: CGPoint(x: centerX - 18, y: baseY),
            control1: CGPoint(x: centerX - radiusX * 0.78, y: baseY + (upper ? 38 : -38)),
            control2: CGPoint(x: centerX - radiusX * 0.32, y: baseY + (upper ? 10 : -10))
        )
        path.addCurve(
            to: CGPoint(x: centerX + 18, y: baseY),
            control1: CGPoint(x: centerX - 8, y: baseY + (upper ? -4 : 4)),
            control2: CGPoint(x: centerX + 8, y: baseY + (upper ? -4 : 4))
        )
        path.addCurve(
            to: CGPoint(x: centerX + radiusX, y: baseY + (upper ? 96 : -96)),
            control1: CGPoint(x: centerX + radiusX * 0.32, y: baseY + (upper ? 10 : -10)),
            control2: CGPoint(x: centerX + radiusX * 0.78, y: baseY + (upper ? 38 : -38))
        )
        return path
    }

    private func toothPoint(label: String, centerX: CGFloat, upperY: CGFloat, lowerY: CGFloat, radiusX: CGFloat) -> CGPoint {
        let quadrant = Int(label.prefix(1)) ?? 1
        let digit = CGFloat(Int(label.suffix(1)) ?? 1)
        let side: CGFloat = (quadrant == 1 || quadrant == 4) ? -1 : 1
        let isUpper = quadrant == 1 || quadrant == 2
        let t = (digit - 1) / 7
        let distance = 17 + t * (radiusX - 22)
        let posteriorCurve = t * t * 96
        let y = isUpper ? upperY + posteriorCurve : lowerY - posteriorCurve
        return CGPoint(x: centerX + side * distance, y: y)
    }

    private func labelPoint(label: String, centerX: CGFloat, upperY: CGFloat, lowerY: CGFloat, radiusX: CGFloat) -> CGPoint {
        let tooth = toothPoint(label: label, centerX: centerX, upperY: upperY, lowerY: lowerY, radiusX: radiusX)
        let quadrant = Int(label.prefix(1)) ?? 1
        let digit = CGFloat(Int(label.suffix(1)) ?? 1)
        let side: CGFloat = (quadrant == 1 || quadrant == 4) ? -1 : 1
        let isUpper = quadrant == 1 || quadrant == 2
        let t = (digit - 1) / 7
        let xOffset = side * (10 + t * 16)
        let yOffset = (isUpper ? -1 : 1) * (22 - t * 7)
        return CGPoint(x: tooth.x + xOffset, y: tooth.y + yOffset)
    }

    private func toothKind(label: String) -> ToothKind {
        switch Int(label.suffix(1)) ?? 1 {
        case 1, 2: return .incisor
        case 3: return .canine
        case 4, 5: return .premolar
        default: return .molar
        }
    }
}

private enum ToothKind {
    case incisor
    case canine
    case premolar
    case molar
}

private struct NumberedToothBadge: View {
    var tooth: ToothMapDiagram.ToothNumber
    var point: CGPoint
    var labelPoint: CGPoint
    var numberingSystem: ToothNumberingSystem
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
        }
        .frame(width: toothSize.width, height: toothSize.height)
        .position(point)
        Text(tooth.label(for: numberingSystem))
            .font(.system(size: 10, weight: .semibold, design: .rounded))
            .monospacedDigit()
            .foregroundStyle(.primary)
            .padding(.horizontal, 4)
            .padding(.vertical, 2)
            .background(.thinMaterial, in: Capsule())
            .position(labelPoint)
    }

    private var toothSize: CGSize {
        switch kind {
        case .incisor: return CGSize(width: 24, height: 32)
        case .canine: return CGSize(width: 26, height: 35)
        case .premolar: return CGSize(width: 29, height: 30)
        case .molar: return CGSize(width: 32, height: 30)
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
