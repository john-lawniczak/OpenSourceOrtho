import Foundation

/// Bounded PLY reader: ASCII and binary in both byte orders, including scalar vertex attributes.
enum PLYImport {
    struct Property { let name: String; let type: String; let countType: String? }
    struct Element { let name: String; let count: Int; var properties: [Property] }
    static let types: [String: (Int, Bool, Bool)] = [
        "char": (1,true,false), "int8": (1,true,false), "uchar": (1,false,false), "uint8": (1,false,false),
        "short": (2,true,false), "int16": (2,true,false), "ushort": (2,false,false), "uint16": (2,false,false),
        "int": (4,true,false), "int32": (4,true,false), "uint": (4,false,false), "uint32": (4,false,false),
        "float": (4,true,true), "float32": (4,true,true), "double": (8,true,true), "float64": (8,true,true)
    ]

    static func decode(_ data: Data) throws -> STLMesh {
        let prefix = data.prefix(65536)
        guard let marker = prefix.range(of: Data("\nend_header\n".utf8)) ?? prefix.range(of: Data("\nend_header\r\n".utf8)),
              let header = String(data: data[..<marker.upperBound], encoding: .ascii) else { throw STLMesh.LoadError.invalid }
        let (format, elements) = try parseHeader(header)
        var reader = try Cursor(data: data, offset: marker.upperBound, format: format)
        var points: [Float] = [], triangles: [Float] = []
        for element in elements {
            if element.name == "vertex" { points.reserveCapacity(element.count * 3) }
            for row in 0..<element.count {
                if row % 1024 == 0 { try Task.checkCancellation() }
                var xyz = [Float](repeating: .nan, count: 3), face: [Int]?
                for property in element.properties {
                    if let countType = property.countType {
                        let count = try reader.integer(countType)
                        guard (3...64).contains(count) else { throw STLMesh.LoadError.invalid }
                        face = try (0..<count).map { _ in try reader.integer(property.type) }
                    } else {
                        let value = try reader.value(property.type)
                        if let axis = ["x","y","z"].firstIndex(of: property.name) { xyz[axis] = Float(value) }
                    }
                }
                if element.name == "vertex" {
                    guard xyz.allSatisfy({ $0.isFinite && abs($0) <= 1_000_000 }) else { throw STLMesh.LoadError.invalid }
                    points.append(contentsOf: xyz)
                } else {
                    guard let face else { throw STLMesh.LoadError.invalid }
                    try ScanImport.appendFace(face, points: points, triangles: &triangles)
                }
            }
        }
        guard reader.atEnd() else { throw STLMesh.LoadError.invalid }
        return try STLMesh.build(triangles.isEmpty ? points : triangles, pointCloud: triangles.isEmpty)
    }

    private static func parseHeader(_ header: String) throws -> (String, [Element]) {
        let lines = header.split(whereSeparator: \.isNewline)
        guard lines.first == "ply" else { throw STLMesh.LoadError.invalid }
        var format = "", elements: [Element] = []
        for line in lines.dropFirst() {
            let p = line.split(whereSeparator: \.isWhitespace).map(String.init)
            guard let command = p.first else { continue }
            switch command {
            case "format":
                guard p.count == 3, p[2] == "1.0", format.isEmpty,
                      ["ascii", "binary_little_endian", "binary_big_endian"].contains(p[1]) else { throw STLMesh.LoadError.invalid }
                format = p[1]
            case "element":
                guard p.count == 3, ["vertex","face"].contains(p[1]), !elements.contains(where: { $0.name == p[1] }),
                      let n = Int(p[2]), n >= 0, n <= STLMesh.maxTriangles else { throw STLMesh.LoadError.invalid }
                elements.append(Element(name: p[1], count: n, properties: []))
            case "property":
                guard !elements.isEmpty else { throw STLMesh.LoadError.invalid }
                let last = elements.count-1
                let property: Property
                if p.count == 5, p[1] == "list", types[p[2]]?.2 == false, types[p[3]]?.2 == false,
                   elements[last].name == "face", ["vertex_indices","vertex_index"].contains(p[4]) {
                    property = Property(name: p[4], type: p[3], countType: p[2])
                } else if p.count == 3, types[p[1]] != nil {
                    property = Property(name: p[2], type: p[1], countType: nil)
                } else { throw STLMesh.LoadError.invalid }
                guard elements[last].properties.count < 32,
                      !elements[last].properties.contains(where: { $0.name == property.name }),
                      !(property.countType != nil && elements[last].properties.contains(where: { $0.countType != nil })) else { throw STLMesh.LoadError.invalid }
                elements[last].properties.append(property)
            case "comment", "obj_info", "end_header": break
            default: throw STLMesh.LoadError.invalid
            }
        }
        guard !format.isEmpty, elements.first?.name == "vertex", elements.first?.count ?? 0 > 0,
              Set(elements[0].properties.map(\.name)).isSuperset(of: ["x","y","z"]) else { throw STLMesh.LoadError.invalid }
        return (format, elements)
    }

    private struct Cursor {
        let data: Data, format: String
        var offset: Int
        var lines: IndexingIterator<[Substring]>
        var tokens: IndexingIterator<[Substring]> = [].makeIterator()
        init(data: Data, offset: Int, format: String) throws {
            self.data = data; self.offset = offset; self.format = format
            if format == "ascii" {
                try ScanImport.validateTextLines(data[offset...])
                guard let text = String(data: data[offset...], encoding: .ascii) else { throw STLMesh.LoadError.invalid }
                lines = text.split(whereSeparator: \.isNewline).makeIterator()
            } else { lines = [].makeIterator() }
        }
        mutating func token() -> Substring? {
            if let next = tokens.next() { return next }
            while let line = lines.next() {
                tokens = line.split(whereSeparator: \.isWhitespace).makeIterator()
                if let next = tokens.next() { return next }
            }
            return nil
        }
        mutating func value(_ name: String) throws -> Double {
            guard let (size, signed, floating) = PLYImport.types[name] else { throw STLMesh.LoadError.invalid }
            let value: Double
            if format == "ascii" {
                guard let t = token(), let v = Double(t) else { throw STLMesh.LoadError.invalid }
                value = v
            } else {
                guard offset + size <= data.count else { throw STLMesh.LoadError.invalid }
                var bits: UInt64 = 0
                for i in 0..<size {
                    let shift = format == "binary_little_endian" ? i : size-1-i
                    bits |= UInt64(data[offset+i]) << (shift*8)
                }
                offset += size
                if floating { value = size == 4 ? Double(Float(bitPattern: UInt32(bits))) : Double(bitPattern: bits) }
                else if signed && bits & (1 << (size*8-1)) != 0 { value = Double(Int64(bits) - (1 << (size*8))) }
                else { value = Double(bits) }
            }
            guard value.isFinite else { throw STLMesh.LoadError.invalid }
            if !floating {
                let upper = pow(2.0, Double(size*8 - (signed ? 1 : 0))) - 1
                let lower = signed ? -upper-1 : 0
                guard value.rounded(.towardZero) == value, value >= lower, value <= upper else { throw STLMesh.LoadError.invalid }
            }
            return value
        }
        mutating func integer(_ type: String) throws -> Int {
            let v = try value(type)
            guard v >= Double(Int32.min), v <= Double(UInt32.max), v.rounded(.towardZero) == v else { throw STLMesh.LoadError.invalid }
            return Int(v)
        }
        mutating func atEnd() -> Bool { format == "ascii" ? token() == nil : offset == data.count }
    }
}
