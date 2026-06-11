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
        let shouldStopAccessing = url.startAccessingSecurityScopedResource()
        defer {
            if shouldStopAccessing {
                url.stopAccessingSecurityScopedResource()
            }
        }

        let byteCount = ((try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize) ?? 0)
        let previewData = try? Data(contentsOf: url)
        addScan(
            SelectedScan(
                fileName: url.lastPathComponent,
                arch: inferredArch(from: url.lastPathComponent),
                byteCount: byteCount,
                modality: modality
            )
        )
        if let previewData {
            previewScans.append(
                PreviewScan(
                    fileName: url.lastPathComponent,
                    modality: modality,
                    data: previewData
                )
            )
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

    func addDevSampleSTL() {
        let url = Bundle.main.url(forResource: "dev-sample-incisor", withExtension: "stl")
        let byteCount = url.flatMap { try? $0.resourceValues(forKeys: [.fileSizeKey]).fileSize } ?? 0
        let previewData = url.flatMap { try? Data(contentsOf: $0) }
        addScan(
            SelectedScan(
                fileName: "dev-sample-incisor.stl",
                arch: "upper",
                byteCount: byteCount,
                modality: "stl"
            )
        )
        if let previewData {
            previewScans.append(PreviewScan(fileName: "dev-sample-incisor.stl", modality: "stl", data: previewData))
        }
    }

    /// Posts selected records to the engine and advances to Review.
    func generate() async {
        guard !scans.isEmpty else { return }
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
    var id: String { fileName }
    var fileName: String
    var modality: String
    var data: Data
}

private struct MobileExportPackage: Codable {
    var generatedAt: Date
    var scans: [SelectedScan]
    var result: GeneratePlanResponse?
    var storedReviews: [StoredPlanReview]
    var disclaimer: String
}
