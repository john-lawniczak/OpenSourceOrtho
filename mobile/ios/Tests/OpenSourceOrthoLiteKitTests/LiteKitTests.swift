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

    func testMinimalPlanCarriesNonStlModalities() throws {
        let scans = [
            SelectedScan(fileName: "cbct.zip", byteCount: 1234, modality: "cbct"),
            SelectedScan(fileName: "smile.jpg", byteCount: 5678, modality: "photo"),
        ]
        let plan = LitePlanBuilder.minimalPlan(for: scans)
        let data = try JSONEncoder().encode(plan)
        let json = String(decoding: data, as: UTF8.self)

        XCTAssertTrue(json.contains("\"format\":\"dicom\""))
        XCTAssertTrue(json.contains("\"source\":\"cbct\""))
        XCTAssertTrue(json.contains("\"format\":\"image\""))
        XCTAssertTrue(json.contains("\"source\":\"photo\""))
    }

    func testRequestDefaultsKeepDataLocal() {
        let request = LitePlanBuilder.request(for: [])
        XCTAssertEqual(request.provider, "local")
        XCTAssertFalse(request.shareAcknowledged, "lite must not opt into egress by default")
        XCTAssertTrue(request.acknowledgeEducational)
    }

    func testOnDeviceSynthesisIsSTLOnlyAndCaveated() throws {
        let stlScans = [SelectedScan(fileName: "upper.stl", arch: "upper", byteCount: 100)]
        XCTAssertTrue(OnDevicePlanSynthesizer.canSynthesize(scans: stlScans))

        let cbctScans = [SelectedScan(fileName: "cbct.zip", byteCount: 100, modality: "cbct")]
        XCTAssertFalse(OnDevicePlanSynthesizer.canSynthesize(scans: cbctScans))

        let response = OnDevicePlanSynthesizer.response(for: stlScans)
        XCTAssertEqual(response.source, "mobile-stl-best-effort")
        XCTAssertEqual(response.correctness?.verdict, "CONSISTENT")
        XCTAssertTrue(response.caveat?.contains("STL metadata only") == true)
        XCTAssertTrue(response.warnings?.joined(separator: " ").contains("browser/full engine") == true)
    }

    func testStoredBrowserReviewCarriesOpaqueJson() {
        let review = StoredPlanReview(fileName: "case-review.json", byteCount: 14, jsonText: "{\"ok\":true}")
        XCTAssertEqual(review.fileName, "case-review.json")
        XCTAssertEqual(review.jsonText, "{\"ok\":true}")
        XCTAssertNil(review.caseReview)
        XCTAssertFalse(review.id.isEmpty)
    }

    func testStoredCaseReviewFixtureDecodesForMobileImport() throws {
        let data = try Data(contentsOf: fixtureURL("case-review-v1.json"))
        let stored = try StoredPlanReview.importCaseReview(fileName: "case-review-v1.json", data: data)
        let review = try XCTUnwrap(stored.caseReview)

        XCTAssertEqual(review.schema, "orthoplan-case-review-v1")
        XCTAssertEqual(review.kind, "stored-review")
        XCTAssertEqual(review.reviewTier.tier, "stl-only")
        XCTAssertFalse(review.reviewTier.rootBoneAware)
        XCTAssertEqual(review.unresolvedDataGaps.count, 5)
        XCTAssertFalse(review.editable.inMobile)
        XCTAssertTrue(review.editable.requiresBrowserEngine)
        XCTAssertEqual(review.handoff.openURL?.absoluteString, "https://ortho.example/app/?case=golden-case-001")
        XCTAssertEqual(review.handoff.deepLinkURL?.scheme, "orthoplan")
        XCTAssertEqual(review.handoff.qrPayload, review.handoff.openUrl)
    }

    func testStoredCaseReviewImportRejectsNonStoredReviewJson() throws {
        let data = #"{"ok":true}"#.data(using: .utf8)!
        XCTAssertThrowsError(try StoredPlanReview.importCaseReview(fileName: "bad.json", data: data))
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

private func fixtureURL(_ name: String) throws -> URL {
    let testFile = URL(fileURLWithPath: #filePath)
    let repoRoot = testFile
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
        .deletingLastPathComponent()
    return repoRoot.appendingPathComponent("fixtures").appendingPathComponent(name)
}
