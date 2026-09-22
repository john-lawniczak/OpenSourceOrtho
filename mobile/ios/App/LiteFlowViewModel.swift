import Foundation
import OpenSourceOrthoLiteKit

/// Drives the lite flow for the SwiftUI screens. All real work delegates to
/// `OpenSourceOrthoLiteKit`; this only holds view state.
@MainActor
final class LiteFlowViewModel: ObservableObject {
    @Published var step: LiteStep = .upload
    @Published var scans: [SelectedScan] = []
    @Published var isGenerating = false
    @Published var result: GeneratePlanResponse?
    @Published var errorMessage: String?
    @Published var storedReviews: [StoredPlanReview] = []
    @Published var previewScans: [PreviewScan] = []

    private var importTasks: [UUID: Task<Void, Never>] = [:]
    private let client: EngineClient

    init(client: EngineClient) {
        self.client = client
    }

    func addScan(_ scan: SelectedScan) {
        scans.append(scan)
        step = .teethAndTime
    }

    func navigate(to step: LiteStep) {
        self.step = step
    }

    func addFile(url: URL, modality: String) {
        let surface = ["stl", "scan"].contains(modality)
        if surface && !ScanImport.supports(url.lastPathComponent) {
            errorMessage = "Unsupported scan. Export \(ScanImport.formats) from your scanner."
            return
        }
        // Retained upload bytes are bounded independently of the decoded surface budget.
        if surface && previewScans.filter({ ["stl", "scan"].contains($0.modality) }).count >= 2 {
            errorMessage = "Two scan files can be previewed together. Reset the case to replace them."
            return
        }
        let access = url.startAccessingSecurityScopedResource()
        let byteCount = (try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0
        addScan(SelectedScan(fileName: url.lastPathComponent, arch: inferredArch(from: url.lastPathComponent),
                             byteCount: byteCount, modality: modality))
        guard surface else {
            if access { url.stopAccessingSecurityScopedResource() }
            return
        }
        let preview = PreviewScan(fileName: url.lastPathComponent, modality: modality)
        previewScans.append(preview)
        importTasks[preview.id] = Task {
            defer { importTasks[preview.id] = nil }
            let reader = Task.detached(priority: .userInitiated) {
                defer { if access { url.stopAccessingSecurityScopedResource() } }
                return Result { try ScanImport.readBounded(url) }
            }
            let result = await withTaskCancellationHandler { await reader.value } onCancel: { reader.cancel() }
            // Reset or replacement must never resurrect a stale upload.
            guard let index = previewScans.firstIndex(where: { $0.id == preview.id }) else { return }
            switch result {
            case .success(let data): previewScans[index].data = data
            case .failure(let error): previewScans[index].error = "Could not read scan: \(error.localizedDescription)"
            }
        }
    }

    func addPhotoData(fileName: String, data: Data) {
        addScan(
            SelectedScan(
                fileName: fileName,
                byteCount: data.count,
                modality: "photo"
            )
        )
        previewScans.append(PreviewScan(fileName: fileName, modality: "photo", data: data))
    }

    /// Posts selected records to the engine and advances to Review.
    func generate() async {
        guard !scans.isEmpty else { return }
        guard !scans.contains(where: { $0.isSurfaceScan && !$0.isSTL }) else {
            errorMessage = "Use the browser/full engine for review of other scan formats."
            return
        }
        isGenerating = true
        errorMessage = nil
        defer { isGenerating = false }
        do {
            let response = try await client.generatePlan(LitePlanBuilder.request(for: scans))
            result = response
            step = .review
        } catch let EngineError.rejected(errors) {
            errorMessage = errors.joined(separator: "\n")
        } catch let EngineError.offline(message) {
            synthesizeOnDeviceOrReport("Engine offline. \(message)")
        } catch {
            synthesizeOnDeviceOrReport("Unexpected error: \(error.localizedDescription)")
        }
    }

    func importBrowserReview(url: URL) {
        let shouldStopAccessing = url.startAccessingSecurityScopedResource()
        defer {
            if shouldStopAccessing {
                url.stopAccessingSecurityScopedResource()
            }
        }

        do {
            let data = try Data(contentsOf: url)
            storedReviews.append(
                try StoredPlanReview.importCaseReview(
                    fileName: url.lastPathComponent,
                    data: data
                )
            )
            errorMessage = nil
        } catch {
            errorMessage = "Could not import browser review: \(error.localizedDescription)"
        }
    }

    func showPrintAndSend() { step = .printAndSend }

    func exportPackageURL() throws -> URL {
        let payload = MobileExportPackage(
            generatedAt: Date(),
            scans: scans,
            result: result,
            storedReviews: storedReviews,
            disclaimer: SafetyText.disclaimer
        )
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        encoder.dateEncodingStrategy = .iso8601

        let url = FileManager.default.temporaryDirectory
            .appendingPathComponent("opensource-ortho-print-package")
            .appendingPathExtension("json")
        try encoder.encode(payload).write(to: url, options: .atomic)
        return url
    }

    func reset() {
        importTasks.values.forEach { $0.cancel() }
        importTasks = [:]
        scans = []
        previewScans = []
        result = nil
        errorMessage = nil
        step = .upload
    }

    private func synthesizeOnDeviceOrReport(_ engineMessage: String) {
        guard OnDevicePlanSynthesizer.canSynthesize(scans: scans) else {
            errorMessage = "\(engineMessage)\nMobile generation is STL-only. Open the browser/full engine for CBCT/DICOM, segmentation, and plan changes."
            return
        }
        result = OnDevicePlanSynthesizer.response(for: scans)
        errorMessage = "Using limited on-device STL synthesis because the engine was unavailable. Open the browser/full engine for mesh-backed edits, CBCT/DICOM, and print-critical review."
        step = .review
    }

    private func inferredArch(from fileName: String) -> String? {
        let lowercased = fileName.lowercased()
        if lowercased.contains("upper") || lowercased.contains("maxillary") {
            return "upper"
        }
        if lowercased.contains("lower") || lowercased.contains("mandibular") {
            return "lower"
        }
        return nil
    }
}

struct PreviewScan: Identifiable {
    let id = UUID()
    var fileName: String
    var modality: String
    var data: Data? = nil
    var error: String? = nil
}

private struct MobileExportPackage: Codable {
    var generatedAt: Date
    var scans: [SelectedScan]
    var result: GeneratePlanResponse?
    var storedReviews: [StoredPlanReview]
    var disclaimer: String
}
