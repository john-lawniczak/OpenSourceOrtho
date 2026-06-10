import Foundation

/// Reads app identity from the bundle that owns the SwiftUI app target.
enum AppIdentity {
    static var installedVersionDisplay: String {
        installedVersionDisplay(bundle: .main)
    }

    static func installedVersionDisplay(bundle: Bundle) -> String {
        let version = string(for: "CFBundleShortVersionString", in: bundle) ?? "Unknown"
        guard let build = string(for: "CFBundleVersion", in: bundle), !build.isEmpty else {
            return "Version \(version)"
        }
        return "Version \(version) (\(build))"
    }

    private static func string(for key: String, in bundle: Bundle) -> String? {
        bundle.object(forInfoDictionaryKey: key) as? String
    }
}
