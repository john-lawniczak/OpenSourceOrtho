import XCTest

final class ScanViewerUITests: XCTestCase {
    func testBothArchesAndContinuousRecordedComparison() {
        let app = XCUIApplication()
        app.launch()
        app.buttons["Teeth"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["USER_ONE · scan comparison"].waitForExistence(timeout: 10))
        checkSurface(app, id: "surface-0", faces: "330,309")
        checkSurface(app, id: "surface-1", faces: "286,801")
        capture(app, "baseline-both")
        let slider = app.sliders["Compare recorded scans"]
        XCTAssertTrue(slider.exists)
        slider.adjust(toNormalizedSliderPosition: 0.5)
        XCTAssertTrue(app.staticTexts["comparison-status"].label.contains("reveal"))
        capture(app, "comparison-both")
        slider.adjust(toNormalizedSliderPosition: 1)
        checkSurface(app, id: "surface-0", faces: "332,227")
        checkSurface(app, id: "surface-1", faces: "265,329")
        capture(app, "week7-both")
        app.buttons["Lower"].tap()
        checkSurface(app, id: "surface-0", faces: "265,329")
        XCTAssertFalse(app.staticTexts["surface-1"].exists)
        app.buttons["Reset view"].tap()
        app.buttons["Upper"].tap()
        checkSurface(app, id: "surface-0", faces: "332,227")
        app.buttons["Both"].tap()
        slider.adjust(toNormalizedSliderPosition: 0)
        checkSurface(app, id: "surface-1", faces: "286,801")
        XCTAssertFalse(app.buttons["Generate for review"].exists)
    }
    private func checkSurface(_ app: XCUIApplication, id: String, faces: String) {
        let count = app.staticTexts[id]
        XCTAssertTrue(count.waitForExistence(timeout: 45))
        XCTAssertTrue(count.label.contains(faces), count.label)
    }
    private func capture(_ app: XCUIApplication, _ name: String) {
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name; attachment.lifetime = .keepAlways; add(attachment)
    }
}
