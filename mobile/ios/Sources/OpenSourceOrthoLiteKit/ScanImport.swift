import Foundation

/// Scanner exports stay on-device. Texture paths are never opened or fetched.
public enum ScanImport {
    public static let extensions = ["stl", "obj", "ply", "asc", "xyz", "pts"]
    public static let formats = "STL, OBJ, PLY, ASC, XYZ, PTS"
    public static func supports(_ filename: String) -> Bool {
        extensions.contains(URL(fileURLWithPath: filename).pathExtension.lowercased())
    }

    public static func decode(_ data: Data, filename: String) throws -> STLMesh {
        guard data.count <= STLMesh.maxBytes else { throw STLMesh.LoadError.tooLarge }
        switch URL(fileURLWithPath: filename).pathExtension.lowercased() {
        case "stl": return try STLMesh.decode(data)
        case "obj": return try textMesh(data, obj: true, counted: false)
        case "ply": return try PLYImport.decode(data)
        case "asc", "xyz": return try textMesh(data, obj: false, counted: false)
        case "pts": return try textMesh(data, obj: false, counted: true)
        default: throw STLMesh.LoadError.invalid
        }
    }

    private static func textMesh(_ data: Data, obj: Bool, counted: Bool) throws -> STLMesh {
        try validateTextLines(data)
        guard let text = String(data: data, encoding: .utf8) else { throw STLMesh.LoadError.invalid }
        var points: [Float] = [], triangles: [Float] = []
        var expected: Int?
        for (lineIndex, line) in text.split(whereSeparator: \.isNewline).enumerated() {
            if lineIndex % 1024 == 0 { try Task.checkCancellation() }
            let tokens = line.split(separator: "#", maxSplits: 1, omittingEmptySubsequences: false)[0]
                .split(whereSeparator: \.isWhitespace)
            if tokens.isEmpty { continue }
            if counted && expected == nil {
                guard tokens.count == 1, let count = Int(tokens[0]), count > 0,
                      count <= STLMesh.maxTriangles else { throw STLMesh.LoadError.invalid }
                expected = count; continue
            }
            if obj && tokens[0] == "f" {
                let indices = try tokens.dropFirst().map { token -> Int in
                    guard let raw = Int(token.split(separator: "/", omittingEmptySubsequences: false)[0]), raw != 0 else {
                        throw STLMesh.LoadError.invalid
                    }
                    return raw > 0 ? raw - 1 : points.count / 3 + raw
                }
                try appendFace(indices, points: points, triangles: &triangles)
            } else if !obj || tokens[0] == "v" {
                let coordinates = obj ? Array(tokens.dropFirst()) : Array(tokens)
                guard coordinates.count >= 3,
                      !obj || [3,4,6].contains(coordinates.count),
                      !obj || coordinates.count != 4 || Float(coordinates[3]) == 1 else { throw STLMesh.LoadError.invalid }
                for token in coordinates.prefix(3) {
                    guard let value = Float(token), value.isFinite, abs(value) <= 1_000_000 else {
                        throw STLMesh.LoadError.invalid
                    }
                    points.append(value)
                }
                guard points.count / 3 <= STLMesh.maxTriangles else { throw STLMesh.LoadError.tooLarge }
            } else if ["l", "curv", "curv2", "surf"].contains(String(tokens[0])) {
                throw STLMesh.LoadError.invalid
            }
        }
        if let expected, expected != points.count / 3 { throw STLMesh.LoadError.invalid }
        return try STLMesh.build(triangles.isEmpty ? points : triangles, pointCloud: triangles.isEmpty)
    }

    /// Triangle and convex planar polygon exports; reject ambiguous concave/non-planar faces.
    static func appendFace(_ indices: [Int], points: [Float], triangles: inout [Float]) throws {
        guard (3...64).contains(indices.count), indices.allSatisfy({ $0 >= 0 && $0 < points.count / 3 }),
              Set(indices).count == indices.count else { throw STLMesh.LoadError.invalid }
        guard triangles.count / 9 + indices.count - 2 <= STLMesh.maxTriangles else { throw STLMesh.LoadError.tooLarge }
        if indices.count > 3 { try validatePolygon(indices, points: points) }
        for i in 1..<(indices.count - 1) {
            for index in [indices[0], indices[i], indices[i+1]] {
                triangles.append(contentsOf: points[index*3..<index*3+3])
            }
        }
    }

    private static func validatePolygon(_ indices: [Int], points: [Float]) throws {
        let p = indices.map { i in (0..<3).map { Double(points[i*3+$0]) } }
        func cross(_ a: [Double], _ b: [Double]) -> [Double] {
            [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
        }
        let a = (0..<3).map { p[1][$0]-p[0][$0] }, b = (0..<3).map { p[2][$0]-p[1][$0] }
        let n = cross(a,b), length = sqrt(n.reduce(0) { $0+$1*$1 })
        guard length > 0 else { throw STLMesh.LoadError.invalid }
        for i in p.indices {
            let d = (0..<3).map { p[i][$0]-p[0][$0] }
            let distance = zip(d,n).reduce(0) { $0+$1.0*$1.1 } / length
            let u = (0..<3).map { p[(i+1)%p.count][$0]-p[i][$0] }
            guard abs(distance) <= 0.0001 else { throw STLMesh.LoadError.invalid }
            // Every other vertex must lie strictly on the same side of this edge.
            // Consecutive turns alone incorrectly accept self-intersecting stars.
            for j in p.indices where j != i && j != (i+1)%p.count {
                let v = (0..<3).map { p[j][$0]-p[i][$0] }
                let side = zip(cross(u,v),n).reduce(0) { $0+$1.0*$1.1 }
                guard side > 0 else { throw STLMesh.LoadError.invalid }
            }
        }
    }
}
