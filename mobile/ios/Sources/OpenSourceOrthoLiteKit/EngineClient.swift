import Foundation

/// Errors surfaced to the UI. The lite app never falls back to an on-device
/// plan; any failure becomes an explicit "engine offline / rejected" state.
public enum EngineError: Error, Sendable, Equatable {
    case offline(String)
    case rejected([String])
    case decode(String)
}

/// Thin async HTTP client over the OpenSource Ortho engine. Implements only the
/// lite-flow endpoints from ../../API_CONTRACT.md.
public struct EngineClient: Sendable {
    public let config: EngineConfig
    private let session: URLSession

    public init(config: EngineConfig = .default, session: URLSession = .shared) {
        self.config = config
        self.session = session
    }

    /// `POST /api/generate-plan` - the core lite call.
    public func generatePlan(_ request: GeneratePlanRequest) async throws -> GeneratePlanResponse {
        let data = try await post(path: "/api/generate-plan", body: request)
        let decoder = JSONDecoder()
        let response: GeneratePlanResponse
        do {
            response = try decoder.decode(GeneratePlanResponse.self, from: data)
        } catch {
            throw EngineError.decode("Could not read engine response: \(error)")
        }
        if !response.ok {
            throw EngineError.rejected(response.errors ?? ["request rejected"])
        }
        return response
    }

    /// `GET /api/mesh/<id>` - raw mesh bytes for the 3D preview, or nil if the
    /// engine has no registered asset (caller falls back to schematic teeth).
    public func meshBytes(assetID: String) async throws -> Data? {
        guard let encoded = assetID.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed),
              let url = URL(string: "/api/mesh/\(encoded)", relativeTo: config.baseURL) else {
            return nil
        }
        do {
            let (data, response) = try await session.data(from: url)
            guard let http = response as? HTTPURLResponse, http.statusCode == 200 else {
                return nil
            }
            return data
        } catch {
            throw EngineError.offline("Engine unreachable: \(error.localizedDescription)")
        }
    }

    private func post<Body: Encodable>(path: String, body: Body) async throws -> Data {
        guard let url = URL(string: path, relativeTo: config.baseURL) else {
            throw EngineError.offline("Bad engine URL for \(path)")
        }
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let encoder = JSONEncoder()
        req.httpBody = try encoder.encode(body)
        do {
            let (data, _) = try await session.data(for: req)
            return data
        } catch {
            throw EngineError.offline("Engine unreachable: \(error.localizedDescription)")
        }
    }
}
