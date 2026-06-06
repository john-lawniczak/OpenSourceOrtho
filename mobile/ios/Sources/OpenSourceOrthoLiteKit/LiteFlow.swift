import Foundation

/// The four-step lite flow shared with Android (../../README.md). Pure value
/// type so it can be driven from a SwiftUI view model and unit-tested.
public enum LiteStep: Int, CaseIterable, Sendable {
    case upload      // pick an STL scan from the device
    case generate    // one tap -> POST /api/generate-plan
    case review      // verdict + findings from the engine
    case progression // staged movement + 3D over time

    public var title: String {
        switch self {
        case .upload:      return "Upload scan"
        case .generate:    return "Generate plan"
        case .review:      return "Review"
        case .progression: return "Progression"
        }
    }
}

/// A locally-selected scan file. Lite uploads metadata + registers bytes with
/// the engine's mesh workspace; plan JSON never carries mesh bytes.
public struct SelectedScan: Sendable, Equatable {
    public var fileName: String
    public var arch: String?       // "upper" | "lower" | nil (unspecified)
    public var byteCount: Int

    public init(fileName: String, arch: String? = nil, byteCount: Int) {
        self.fileName = fileName
        self.arch = arch
        self.byteCount = byteCount
    }
}

/// Builds the minimal plan-shaped payload the lite flow sends to
/// `POST /api/generate-plan`. The engine fills in defaults and is the source of
/// truth for the full `TreatmentPlan` shape; lite only seeds scan metadata.
public enum LitePlanBuilder {
    public static func minimalPlan(for scans: [SelectedScan]) -> [String: AnyCodable] {
        let scanObjects: [AnyCodable] = scans.map { scan in
            var fields: [String: AnyCodable] = [
                "file_name": AnyCodable(.string(scan.fileName)),
            ]
            if let arch = scan.arch {
                fields["arch"] = AnyCodable(.string(arch))
            }
            return AnyCodable(.object(fields))
        }
        return ["scans": AnyCodable(.array(scanObjects))]
    }

    public static func request(for scans: [SelectedScan]) -> GeneratePlanRequest {
        GeneratePlanRequest(plan: minimalPlan(for: scans))
    }
}
