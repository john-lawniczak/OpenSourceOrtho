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
        addScan(
            SelectedScan(
                fileName: url.lastPathComponent,
                arch: inferredArch(from: url.lastPathComponent),
                byteCount: byteCount,
                modality: modality
            )
        )
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
            errorMessage = "Engine offline. \(message)"
        } catch {
            errorMessage = "Unexpected error: \(error.localizedDescription)"
        }
    }

    func showPrintAndSend() { step = .printAndSend }

    func exportPackageURL() throws -> URL {
        let payload = MobileExportPackage(
            generatedAt: Date(),
            scans: scans,
            result: result,
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
        result = nil
        errorMessage = nil
        step = .upload
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

private struct MobileExportPackage: Codable {
    var generatedAt: Date
    var scans: [SelectedScan]
    var result: GeneratePlanResponse?
    var disclaimer: String
}
