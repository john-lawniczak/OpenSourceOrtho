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
        let scanObjects: [AnyCodable] = scans.enumerated().map { index, scan in
            let asset: [String: AnyCodable] = [
                "id": AnyCodable(.string(assetId(for: scan.fileName, index: index))),
                "format": AnyCodable(.string("stl")),
                "provenance": AnyCodable(.string("patient-derived")),
                "units": AnyCodable(.string("unverified")),
                "vertex_count": AnyCodable(.int(0)),
                "face_count": AnyCodable(.int(0)),
                "reference": AnyCodable(.string(scan.fileName)),
            ]
            var fields: [String: AnyCodable] = [
                "asset": AnyCodable(.object(asset)),
                "source": AnyCodable(.string("intraoral-scan")),
            ]
            if let arch = engineArch(scan.arch) {
                fields["arch"] = AnyCodable(.string(arch))
            }
            return AnyCodable(.object(fields))
        }
        return [
            "id": AnyCodable(.string("lite-plan")),
            "title": AnyCodable(.string("Lite plan")),
            "numbering_system": AnyCodable(.string("FDI")),
            "coordinate_frame": AnyCodable(.object(["name": AnyCodable(.string("scan-local"))])),
            "scans": AnyCodable(.array(scanObjects)),
        ]
    }

    public static func request(for scans: [SelectedScan]) -> GeneratePlanRequest {
        GeneratePlanRequest(plan: minimalPlan(for: scans))
    }

    private static func engineArch(_ value: String?) -> String? {
        switch value?.lowercased() {
        case "upper", "maxillary": return "maxillary"
        case "lower", "mandibular": return "mandibular"
        default: return nil
        }
    }

    private static func assetId(for fileName: String, index: Int) -> String {
        let lowered = fileName.lowercased()
        let mapped = lowered.map { char -> Character in
            if char.isLetter || char.isNumber { return char }
            return "-"
        }
        let cleaned = String(mapped).trimmingCharacters(in: CharacterSet(charactersIn: "-"))
        return "lite-\(index)-\(cleaned.isEmpty ? "scan" : cleaned)"
    }
}
