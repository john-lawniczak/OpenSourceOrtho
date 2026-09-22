import Foundation

extension ScanImport {
    /// Enforce the limit while reading, including providers that report no file size.
    public static func readBounded(_ url: URL) throws -> Data {
        let file = try FileHandle(forReadingFrom: url)
        defer { try? file.close() }
        var data = Data()
        while true {
            try Task.checkCancellation()
            guard let chunk = try file.read(upToCount: 262144), !chunk.isEmpty else { break }
            guard chunk.count <= STLMesh.maxBytes - data.count else { throw STLMesh.LoadError.tooLarge }
            data.append(chunk)
        }
        return data
    }
    static func validateTextLines(_ data: Data) throws {
        try data.withUnsafeBytes { (bytes: UnsafeRawBufferPointer) in
            var length = 0
            for (i, byte) in bytes.enumerated() {
                if i % 262144 == 0 { try Task.checkCancellation() }
                length = byte == 10 || byte == 13 ? 0 : length + 1
                guard byte != 0, length <= 16384 else { throw STLMesh.LoadError.invalid }
            }
        }
    }

}
