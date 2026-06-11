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

    public var isSTL: Bool {
        modality.lowercased() == "stl" || fileName.lowercased().hasSuffix(".stl")
    }
}

/// A review/package JSON produced by the full browser/Python workspace and kept
/// on-device for reference. Mobile treats it as opaque; edits still belong in
/// the engine-backed browser workflow.
public struct StoredPlanReview: Codable, Sendable, Equatable, Identifiable {
    public var id: String
    public var fileName: String
    public var byteCount: Int
    public var importedAt: Date
    public var jsonText: String

    public init(fileName: String, byteCount: Int, importedAt: Date = Date(), jsonText: String) {
        self.id = Self.reviewId(fileName: fileName, importedAt: importedAt)
        self.fileName = fileName
        self.byteCount = byteCount
        self.importedAt = importedAt
        self.jsonText = jsonText
    }

    private static func reviewId(fileName: String, importedAt: Date) -> String {
        let cleaned = fileName.lowercased().map { char -> Character in
            if char.isLetter || char.isNumber { return char }
            return "-"
        }
        return "\(String(cleaned))-\(Int(importedAt.timeIntervalSince1970))"
    }
}

/// Best-effort mobile synthesis for STL-only cases when the engine is not
/// reachable. This is intentionally conservative and caveated; CBCT/DICOM stays
/// browser/full-engine only because root/bone-aware work needs heavier local
/// ingestion, registration, and review contracts.
public enum OnDevicePlanSynthesizer {
    public static func canSynthesize(scans: [SelectedScan]) -> Bool {
        !scans.isEmpty && scans.allSatisfy(\.isSTL)
    }

    public static func response(for scans: [SelectedScan]) -> GeneratePlanResponse {
        let stageCount = max(6, scans.count * 6)
        let projectedDays = stageCount * 14
        let plan = LitePlanBuilder.minimalPlan(for: scans).merging(
            [
                "stages": AnyCodable(.array([])),
                "mobile_synthesis": AnyCodable(.object([
                    "mode": AnyCodable(.string("stl-only-best-effort")),
                    "requires_browser_for_edits": AnyCodable(.bool(true)),
                ])),
            ],
            uniquingKeysWith: { _, new in new }
        )
        return GeneratePlanResponse(
            ok: true,
            source: "mobile-stl-best-effort",
            warnings: [
                "Generated on-device from STL metadata only.",
                "Open the browser/full engine for segmentation, mesh-backed editing, CBCT/DICOM, or print-critical review.",
            ],
            steps: [
                PipelineStep(
                    name: "mobile-stl-intake",
                    status: "warning",
                    detail: "STL files were accepted for a limited on-device review."
                ),
                PipelineStep(
                    name: "browser-handoff",
                    status: "warning",
                    detail: "Use the browser workspace for CBCT/DICOM, segmentation, and plan changes."
                ),
            ],
            correctness: Correctness(verdict: "CONSISTENT"),
            stageCount: stageCount,
            timeline: Timeline(
                stageCount: stageCount,
                wearIntervalDays: 14,
                projectedDurationDays: projectedDays,
                projectedDurationWeeks: Double(projectedDays) / 7.0,
                caveat: "Mobile STL-only synthesis is a conservative review artifact. It excludes segmentation, CBCT/DICOM registration, root/bone checks, collision validation from real tooth meshes, and clinical approval."
            ),
            caveat: "This review was synthesized on-device from STL metadata only. Use the browser/full engine for accurate mesh geometry, CBCT/DICOM, plan edits, print-critical exports, and clinician review.",
            plan: AnyCodable(.object(plan))
        )
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
