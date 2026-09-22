import Foundation

/// Observed visits for the bundled case; independent of generated plan stages.
public struct SampleHistory: Decodable {
    public let schema: String
    public let pseudonym: String
    public let specimenId: String
    public let title: String
    public let summary: String
    public let timing: String
    public let limitation: String
    public let context: String
    public let visits: [Visit]
    public let events: [Event]

    public struct Visit: Decodable, Identifiable {
        public let id: String
        public let label: String
        public let date: String
        public let detail: String
        public let arches: [Arch]
    }

    public struct Arch: Decodable {
        public let name: String
        public let previewImage: String
        public let filename: String
        public let sha256: String
        public let faceCount: Int
        public let zeroAreaFaces: Int
        public let displayRotation: [Float]
        public let units: String
    }

    public struct Event: Decodable, Identifiable {
        public let id: String
        public let date: String
        public let label: String
    }

    public static func decode(_ data: Data) throws -> SampleHistory {
        let history = try JSONDecoder().decode(Self.self, from: data)
        guard history.schema == "opensource-ortho-mobile-history-v1",
              !history.visits.isEmpty,
              Set(history.visits.map(\.id)).count == history.visits.count,
              history.visits.allSatisfy({ !$0.arches.isEmpty && $0.arches.allSatisfy { arch in
                  arch.displayRotation.count == 3 && arch.displayRotation.allSatisfy { abs($0) == 1 }
              } }) else {
            throw DecodingError.dataCorrupted(.init(codingPath: [], debugDescription: "Invalid sample history"))
        }
        return history
    }
}
