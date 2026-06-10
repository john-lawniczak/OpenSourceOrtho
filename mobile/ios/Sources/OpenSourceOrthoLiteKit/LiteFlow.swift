import Foundation

/// The four-step lite flow shared with Android (../../README.md). Pure value
/// type so it can be driven from a SwiftUI view model and unit-tested.
public enum LiteStep: Int, CaseIterable, Sendable {
    case upload       // pick CBCT, STL, or photo records from the device
    case teethAndTime // inspect teeth, stages, and timing before generation
    case review       // verdict + findings from the engine
    case printAndSend // export package for print / lab handoff

    public var title: String {
        switch self {
        case .upload:       return "Upload files"
        case .teethAndTime: return "Teeth + time"
        case .review:       return "Review"
        case .printAndSend: return "Print + send"
        }
    }
}

/// A locally-selected scan file. Lite uploads metadata + registers bytes with
/// the engine's mesh workspace; plan JSON never carries mesh bytes.
public struct SelectedScan: Codable, Sendable, Equatable {
    public var fileName: String
    public var arch: String?       // "upper" | "lower" | nil (unspecified)
    public var byteCount: Int
    public var modality: String    // "cbct" | "stl" | "photo"

    public init(fileName: String, arch: String? = nil, byteCount: Int, modality: String = "stl") {
        self.fileName = fileName
        self.arch = arch
        self.byteCount = byteCount
        self.modality = modality
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
                "format": AnyCodable(.string(engineFormat(scan.modality))),
                "provenance": AnyCodable(.string("patient-derived")),
                "units": AnyCodable(.string("unverified")),
                "vertex_count": AnyCodable(.int(0)),
                "face_count": AnyCodable(.int(0)),
                "reference": AnyCodable(.string(scan.fileName)),
            ]
            var fields: [String: AnyCodable] = [
                "asset": AnyCodable(.object(asset)),
                "source": AnyCodable(.string(engineSource(scan.modality))),
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

    private static func engineFormat(_ value: String) -> String {
        switch value.lowercased() {
        case "cbct": return "dicom"
        case "photo": return "image"
        default: return "stl"
        }
    }

    private static func engineSource(_ value: String) -> String {
        switch value.lowercased() {
        case "cbct": return "cbct"
        case "photo": return "photo"
        default: return "intraoral-scan"
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
