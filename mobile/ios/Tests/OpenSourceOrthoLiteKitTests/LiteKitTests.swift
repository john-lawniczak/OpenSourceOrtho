import XCTest
@testable import OpenSourceOrthoLiteKit

final class LiteKitTests: XCTestCase {
    func testMinimalPlanCarriesScanMetadata() throws {
        let scans = [SelectedScan(fileName: "upper.stl", arch: "upper", byteCount: 1234)]
        let plan = LitePlanBuilder.minimalPlan(for: scans)
        let data = try JSONEncoder().encode(plan)
        let json = String(decoding: data, as: UTF8.self)
        XCTAssertTrue(json.contains("\"id\""))
        XCTAssertTrue(json.contains("\"asset\""))
        XCTAssertTrue(json.contains("upper.stl"))
        XCTAssertTrue(json.contains("maxillary"))
        XCTAssertTrue(json.contains("vertex_count"))
        XCTAssertFalse(json.contains("file_name"))
    }

    func testMinimalPlanKeepsDuplicateFilenamesDistinct() throws {
        let scans = [
            SelectedScan(fileName: "scan.stl", arch: "upper", byteCount: 1234),
            SelectedScan(fileName: "scan.stl", arch: "lower", byteCount: 5678),
        ]
        let plan = LitePlanBuilder.minimalPlan(for: scans)
        let data = try JSONEncoder().encode(plan)
        let json = String(decoding: data, as: UTF8.self)

        XCTAssertTrue(json.contains("lite-0-scan-stl"))
        XCTAssertTrue(json.contains("lite-1-scan-stl"))
    }

    func testRequestDefaultsKeepDataLocal() {
        let request = LitePlanBuilder.request(for: [])
        XCTAssertEqual(request.provider, "local")
        XCTAssertFalse(request.shareAcknowledged, "lite must not opt into egress by default")
        XCTAssertTrue(request.acknowledgeEducational)
    }

    func testDecodeGeneratePlanResponseSubset() throws {
        let body = """
        {
          "ok": true,
          "source": "template",
          "correctness": { "verdict": "CONSISTENT", "extra": 1 },
          "stage_count": 12,
          "timeline": {
            "stage_count": 12, "wear_interval_days": 14,
            "projected_duration_days": 168, "projected_duration_weeks": 24.0,
            "caveat": "Projection excludes refinements."
          },
          "caveat": "Plan generation is deterministic ...",
          "plan": { "stages": [] }
        }
        """.data(using: .utf8)!
        let response = try JSONDecoder().decode(GeneratePlanResponse.self, from: body)
        XCTAssertTrue(response.ok)
        XCTAssertEqual(response.correctness?.verdict, "CONSISTENT")
        XCTAssertEqual(response.timeline?.projectedDurationWeeks, 24.0)
    }

    func testVerdictLabelNeverImpliesApproval() {
        // Verdict labels must never use approval/safety language. (The disclaimer
        // itself does say "approved" - but only inside a negation, which is fine.)
        for verdict in ["CONSISTENT", "ISSUES"] {
            let label = SafetyText.verdictLabel(verdict).lowercased()
            for banned in ["safe", "approved", "cleared", "ready"] {
                XCTAssertFalse(label.contains(banned), "verdict label leaked '\(banned)'")
            }
        }
        XCTAssertEqual(SafetyText.verdictLabel("CONSISTENT"), "Internally consistent")
        XCTAssertEqual(SafetyText.verdictLabel("ISSUES"), "Issues found")
    }
}
