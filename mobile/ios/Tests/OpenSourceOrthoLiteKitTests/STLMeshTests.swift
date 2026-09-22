import Foundation
import XCTest
@testable import OpenSourceOrthoLiteKit

final class STLMeshTests: XCTestCase {
    private var root: URL {
        URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
    }

    func testAllOriginalFacesAndBoundsSurviveLoading() throws {
        let history = try SampleHistory.decode(Data(contentsOf: root.appendingPathComponent("mobile/sample-history/history.json")))
        for arch in history.visits.flatMap(\.arches) {
            let url = root.appendingPathComponent("datasets/\(history.specimenId)/\(arch.filename)")
            let mesh = try STLMesh.decode(Data(contentsOf: url))
            XCTAssertEqual(mesh.triangleCount, arch.faceCount, arch.filename)
            XCTAssertEqual(mesh.vertices.count, arch.faceCount * 18)
            XCTAssertTrue(mesh.vertices.allSatisfy(\.isFinite))
            XCTAssertGreaterThan(mesh.span, 50)
            XCTAssertLessThan(mesh.span, 70)
        }
    }

    func testAsciiAndTruncatedOrInvalidScans() throws {
        let ascii = "solid scan\nfacet normal 0 0 1\nouter loop\nvertex 0 0 0\nvertex 1 0 0\nvertex 0 1 0\nendloop\nendfacet\nendsolid scan"
        let mesh = try STLMesh.decode(Data(ascii.utf8))
        XCTAssertEqual(mesh.triangleCount, 1)
        XCTAssertEqual(mesh.center, [0.5, 0.5, 0])
        XCTAssertEqual(Array(mesh.vertices[3...5]), [0, 0, 1])
        for text in ["", "solid scan", ascii.replacingOccurrences(of: "vertex 0 1 0\n", with: ""),
                     ascii.replacingOccurrences(of: "vertex 0 1 0", with: "vertex nan 1 0")] {
            XCTAssertThrowsError(try STLMesh.decode(Data(text.utf8)))
        }
        var binary = Data(repeating: 0, count: 134)
        binary[80] = 2 // Declares two faces, but only contains one.
        XCTAssertThrowsError(try STLMesh.decode(binary))
    }

    func testBinaryHeaderMayStartWithSolid() throws {
        var data = Data(repeating: 0, count: 134)
        data.replaceSubrange(0..<5, with: Data("solid".utf8))
        data[80] = 1
        for offset in [108, 124] {
            var one = Float(1).bitPattern.littleEndian
            withUnsafeBytes(of: &one) { data.replaceSubrange(offset..<offset+4, with: $0) }
        }
        XCTAssertEqual(try STLMesh.decode(data).triangleCount, 1)
    }
}
