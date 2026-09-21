import Foundation
import XCTest
@testable import OpenSourceOrthoLiteKit

final class SampleHistoryTests: XCTestCase {
    private var fixtureURL: URL {
        URL(fileURLWithPath: #filePath)
            .deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("sample-history/history.json")
    }

    func testBundledObservedVisitsKeepSeparateGeometryAndDates() throws {
        let history = try SampleHistory.decode(Data(contentsOf: fixtureURL))
        XCTAssertEqual(history.visits.map(\.date), ["2026-06-05", "2026-09-17"])
        XCTAssertEqual(history.visits.map(\.label), ["Baseline", "Week 7"])
        XCTAssertEqual(Set(history.visits.flatMap(\.arches).map(\.sha256)).count, 4)
        XCTAssertEqual(history.visits[1].arches.map(\.units), ["unverified", "unverified"])
        XCTAssertTrue(history.timing.contains("Five-day"))
        for arch in history.visits.flatMap(\.arches) {
            XCTAssertTrue(FileManager.default.fileExists(
                atPath: fixtureURL.deletingLastPathComponent().appendingPathComponent(arch.previewImage).path
            ))
        }
    }

    func testEmptyVisitListIsRejectedRatherThanShowingSyntheticFallback() throws {
        let data = try Data(contentsOf: fixtureURL)
        var json = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        json["visits"] = []
        XCTAssertThrowsError(try SampleHistory.decode(JSONSerialization.data(withJSONObject: json)))
    }
}
