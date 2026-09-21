import XCTest

final class ScanViewerUITests: XCTestCase {
    func testObservedVisitsRenderCompleteScans() {
        let app = XCUIApplication()
        app.launch()
        app.buttons["Teeth"].firstMatch.tap()
        XCTAssertTrue(app.staticTexts["USER_ONE · scan history"].waitForExistence(timeout: 10))
        checkSurface(app, faces: "330,309", name: "baseline-upper")
        app.buttons["Lower"].tap()
        checkSurface(app, faces: "286,801", name: "baseline-lower")
        app.buttons["Week 7"].tap()
        checkSurface(app, faces: "265,329", name: "week7-lower")
        app.buttons["Upper"].tap()
        checkSurface(app, faces: "332,227", name: "week7-upper")
        app.buttons["Reset view"].tap()
        XCTAssertFalse(app.sliders.firstMatch.exists)
        XCTAssertFalse(app.buttons["Generate for review"].exists)
    }

    private func checkSurface(_ app: XCUIApplication, faces: String, name: String) {
        let count = app.staticTexts["Complete STL surface · \(faces) triangles"]
        XCTAssertTrue(count.waitForExistence(timeout: 30))
        let attachment = XCTAttachment(screenshot: app.screenshot())
        attachment.name = name
        attachment.lifetime = .keepAlways
        add(attachment)
    }
}
