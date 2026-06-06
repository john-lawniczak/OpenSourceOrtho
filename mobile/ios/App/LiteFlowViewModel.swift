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
        step = .generate
    }

    /// One-tap "Generate Plan": posts to the engine and advances to Review.
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

    func showProgression() { step = .progression }

    func reset() {
        scans = []
        result = nil
        errorMessage = nil
        step = .upload
    }
}
