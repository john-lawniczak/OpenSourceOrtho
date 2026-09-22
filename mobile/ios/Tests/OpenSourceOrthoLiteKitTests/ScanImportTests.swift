import Foundation
import XCTest
@testable import OpenSourceOrthoLiteKit

final class ScanImportTests: XCTestCase {
    struct Fixture: Decodable { let filename: String; let triangles: Int?; let points: Int? }
    private var fixtures: URL {
        URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("test-fixtures/scans")
    }
    func testSharedScannerExportsAndMalformedFiles() throws {
        let cases = try JSONDecoder().decode([Fixture].self, from: Data(contentsOf: fixtures.appendingPathComponent("cases.json")))
        for item in cases {
            let data = try Data(contentsOf: fixtures.appendingPathComponent(item.filename))
            if item.triangles == nil && item.points == nil {
                XCTAssertThrowsError(try ScanImport.decode(data, filename: item.filename), item.filename)
            } else {
                let mesh = try ScanImport.decode(data, filename: item.filename)
                XCTAssertEqual(mesh.triangleCount, item.triangles ?? 0, item.filename)
                XCTAssertEqual(mesh.isPointCloud, item.points != nil, item.filename)
                XCTAssertEqual(mesh.vertexCount, item.points ?? (item.triangles! * 3), item.filename)
                XCTAssertTrue(mesh.vertices.allSatisfy(\.isFinite), item.filename)
            }
        }
    }
    func testNonSTLFormatsCannotEnterSTLFallback() throws {
        for ext in ScanImport.extensions {
            let scan = SelectedScan(fileName: "upper.\(ext.uppercased())", byteCount: 20, modality: "scan")
            XCTAssertTrue(scan.isSurfaceScan)
            let encoded = String(decoding: try JSONEncoder().encode(LitePlanBuilder.minimalPlan(for: [scan])), as: UTF8.self)
            XCTAssertTrue(encoded.contains("\"format\":\"\(ext)\""))
            XCTAssertEqual(scan.isSTL, ext == "stl")
            XCTAssertEqual(OnDevicePlanSynthesizer.canSynthesize(scans: [scan]), ext == "stl")
        }
        XCTAssertFalse(SelectedScan(fileName: "upper.obj", byteCount: 20, modality: "stl").isSTL)
        XCTAssertFalse(SelectedScan(fileName: "upper.stl", byteCount: 20, modality: "photo").isSTL)
    }
    func testBoundedReadAndLongTextLines() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let url = directory.appendingPathComponent("scan.xyz")
        try Data("0 0 0\n".utf8).write(to: url)
        XCTAssertEqual(try ScanImport.readBounded(url), Data("0 0 0\n".utf8))
        let file = try FileHandle(forWritingTo: url)
        try file.truncate(atOffset: UInt64(STLMesh.maxBytes + 1)); try file.close()
        XCTAssertThrowsError(try ScanImport.readBounded(url))
        XCTAssertThrowsError(try ScanImport.decode(Data(String(repeating: "1 ", count: 10000).utf8), filename: "scan.xyz"))
    }
    func testCancellationStopsDecoding() async {
        let task = Task {
            while !Task.isCancelled { await Task.yield() }
            return try ScanImport.decode(Data("0 0 0\n".utf8), filename: "cloud.xyz")
        }
        task.cancel()
        do { _ = try await task.value; XCTFail("Cancelled import succeeded") }
        catch { XCTAssertTrue(error is CancellationError) }
    }
}
