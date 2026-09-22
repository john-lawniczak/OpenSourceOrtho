import Foundation
import CryptoKit
import OpenSourceOrthoLiteKit

struct ScanLayer {
    let id: String
    let mesh: STLMesh
    let rotation: [Float]
    let label: String
}
struct ScanPresentation {
    let before: [ScanLayer]
    let after: [ScanLayer]
    func selecting(_ arch: String) -> ScanPresentation {
        guard arch != "Both" else { return self }
        return ScanPresentation(before: before.filter { $0.label == arch }, after: after.filter { $0.label == arch })
    }
}

enum ScanPresentationLoader {
    static func sample(_ history: SampleHistory) throws -> ScanPresentation {
        guard history.visits.count == 2 else { throw STLMesh.LoadError.invalid }
        var layers: [[ScanLayer]] = []
        var vertices = 0
        for visit in history.visits {
            var visitLayers: [ScanLayer] = []
            for arch in visit.arches {
                try Task.checkCancellation()
                guard let url = Bundle.main.url(forResource: arch.filename, withExtension: nil) else { throw CocoaError(.fileNoSuchFile) }
                let data = try ScanImport.readBounded(url)
                let hash = SHA256.hash(data: data).map { String(format: "%02x", $0) }.joined()
                guard hash == arch.sha256 else { throw STLMesh.LoadError.invalid }
                let mesh = try ScanImport.decode(data, filename: arch.filename)
                vertices += mesh.vertexCount
                guard vertices <= 4_500_000 else { throw STLMesh.LoadError.tooLarge }
                visitLayers.append(ScanLayer(id: arch.sha256, mesh: mesh, rotation: arch.displayRotation, label: arch.name))
            }
            layers.append(visitLayers)
        }
        return ScanPresentation(before: layers[0], after: layers[1])
    }
    static func imported(_ scans: [PreviewScan]) throws -> ScanPresentation {
        var layers: [ScanLayer] = []
        var vertices = 0
        for scan in scans {
            if let error = scan.error { throw NSError(domain: "ScanImport", code: 1, userInfo: [NSLocalizedDescriptionKey: error]) }
            guard let data = scan.data else { throw CocoaError(.fileReadUnknown) }
            let mesh = try ScanImport.decode(data, filename: scan.fileName)
            vertices += mesh.vertexCount
            guard vertices <= 3_000_000 else { throw STLMesh.LoadError.tooLarge }
            layers.append(ScanLayer(id: scan.id.uuidString, mesh: mesh, rotation: [1,1,1], label: scan.fileName))
        }
        return ScanPresentation(before: layers, after: [])
    }
}
