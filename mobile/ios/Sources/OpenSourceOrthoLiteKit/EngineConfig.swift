import Foundation

/// Where the lite app reaches the OpenSource Ortho Python engine.
///
/// The engine is the single source of truth (see ../../API_CONTRACT.md); the app
/// never synthesizes a plan on-device. Change `baseURL` in one place to point at
/// a deployed engine. Cleartext HTTP is only for the local dev hosts below.
public struct EngineConfig: Sendable {
    public var baseURL: URL

    public init(baseURL: URL) {
        self.baseURL = baseURL
    }

    /// iOS Simulator reaches the developer's host loopback directly.
    public static let simulator = EngineConfig(baseURL: URL(string: "http://127.0.0.1:8000")!)

    /// Default used by the app shell. Swap for an https engine in production.
    public static let `default` = EngineConfig.simulator
}
