import Foundation

/// Complete STL surfaces, with derived face normals. Never drops triangles for preview.
public struct STLMesh: Sendable {
    public let vertices: [Float] // interleaved position xyz, normal xyz
    public let triangleCount: Int
    public let isPointCloud: Bool
    public var vertexCount: Int { vertices.count / 6 }
    public let center: [Float]
    public let span: Float
    public static let maxTriangles = 1_000_000
    public static let maxBytes = 80 * 1024 * 1024

    public enum LoadError: Error, LocalizedError {
        case invalid, tooLarge
        public var errorDescription: String? {
            switch self {
            case .invalid: return "This scan is empty, incomplete, unsupported, or contains invalid coordinates."
            case .tooLarge: return "This scan exceeds the mobile preview limit. Open it in the browser."
            }
        }
    }

    public static func decode(_ data: Data) throws -> STLMesh {
        guard data.count <= maxBytes else { throw LoadError.tooLarge }
        var positions: [Float] = []
        let count = data.count >= 84 ? Int(uint32(data, 80)) : 0
        if count > 0 && 84 + count * 50 == data.count {
            guard count <= maxTriangles else { throw LoadError.tooLarge }
            positions.reserveCapacity(count * 9)
            for face in 0..<count {
                if face % 4096 == 0 { try Task.checkCancellation() }
                let offset = 84 + face * 50 + 12
                for component in 0..<9 {
                    positions.append(Float(bitPattern: uint32(data, offset + component * 4)))
                }
            }
        } else {
            try ScanImport.validateTextLines(data)
            guard let text = String(data: data, encoding: .utf8),
                  text.trimmingCharacters(in: .whitespacesAndNewlines).hasPrefix("solid"),
                  text.contains("endsolid") else { throw LoadError.invalid }
            for line in text.split(whereSeparator: \.isNewline) {
                if positions.count % 4096 == 0 { try Task.checkCancellation() }
                let parts = line.split(whereSeparator: \.isWhitespace)
                if parts.first != "vertex" { continue }
                guard parts.count == 4 else { throw LoadError.invalid }
                for part in parts.dropFirst() {
                    guard let value = Float(part) else { throw LoadError.invalid }
                    positions.append(value)
                }
                guard positions.count <= maxTriangles * 9 else { throw LoadError.tooLarge }
            }
        }
        return try build(positions)
    }

    static func build(_ positions: [Float], pointCloud: Bool = false) throws -> STLMesh {
        guard positions.count <= maxTriangles * (pointCloud ? 3 : 9) else { throw LoadError.tooLarge }
        guard !positions.isEmpty, positions.count % (pointCloud ? 3 : 9) == 0,
              positions.allSatisfy({ $0.isFinite && abs($0) <= 1_000_000 }) else {
            throw LoadError.invalid
        }
        var low = [Float](repeating: .infinity, count: 3)
        var high = [Float](repeating: -.infinity, count: 3)
        var vertices: [Float] = []
        vertices.reserveCapacity(positions.count * 2)
        for start in stride(from: 0, to: positions.count, by: pointCloud ? 3 : 9) {
            if start % 4096 == 0 { try Task.checkCancellation() }
            if pointCloud {
                for axis in 0..<3 {
                    let value = positions[start + axis]
                    low[axis] = min(low[axis], value); high[axis] = max(high[axis], value)
                    vertices.append(value)
                }
                vertices.append(contentsOf: [0, 0, 1])
                continue
            }
            let a = (0..<3).map { positions[start + 3 + $0] - positions[start + $0] }
            let b = (0..<3).map { positions[start + 6 + $0] - positions[start + $0] }
            let n = [a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]]
            let length = sqrt(n.reduce(0) { $0 + $1*$1 })
            let normal = length > 0 ? n.map { $0 / length } : [0, 0, 1]
            for vertex in 0..<3 {
                for axis in 0..<3 {
                    let value = positions[start + vertex * 3 + axis]
                    low[axis] = min(low[axis], value)
                    high[axis] = max(high[axis], value)
                    vertices.append(value)
                }
                vertices.append(contentsOf: normal)
            }
        }
        let span = (0..<3).map { high[$0] - low[$0] }.max() ?? 0
        guard span > 0 || pointCloud else { throw LoadError.invalid }
        return STLMesh(vertices: vertices, triangleCount: pointCloud ? 0 : positions.count / 9, isPointCloud: pointCloud,
                       center: (0..<3).map { (low[$0] + high[$0]) / 2 }, span: max(span, 0.0001))
    }

    private static func uint32(_ data: Data, _ offset: Int) -> UInt32 {
        UInt32(data[offset]) | UInt32(data[offset + 1]) << 8
            | UInt32(data[offset + 2]) << 16 | UInt32(data[offset + 3]) << 24
    }
}
