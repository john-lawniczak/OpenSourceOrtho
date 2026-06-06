// swift-tools-version:5.9
import PackageDescription

// The platform-agnostic core of the iOS lite app (config, contract models,
// engine client, flow state, safety text) is a SwiftPM library so it compiles
// and unit-tests with `swift test` - no Xcode required for the logic.
//
// The SwiftUI screens and `@main` entry live in `App/` and are added to an
// Xcode app target that depends on this library (see README.md). They are not
// built by SwiftPM because a SwiftUI app entry point needs an app target.
let package = Package(
    name: "OpenSourceOrthoLite",
    // iOS is the deployment target; macOS is declared only so the logic library
    // builds and tests headless on a Mac dev host (`swift build` / `swift test`).
    platforms: [.iOS(.v16), .macOS(.v12)],
    products: [
        .library(name: "OpenSourceOrthoLiteKit", targets: ["OpenSourceOrthoLiteKit"]),
    ],
    targets: [
        .target(
            name: "OpenSourceOrthoLiteKit",
            path: "Sources/OpenSourceOrthoLiteKit"
        ),
        .testTarget(
            name: "OpenSourceOrthoLiteKitTests",
            dependencies: ["OpenSourceOrthoLiteKit"],
            path: "Tests/OpenSourceOrthoLiteKitTests"
        ),
    ]
)
