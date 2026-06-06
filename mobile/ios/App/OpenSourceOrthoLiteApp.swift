import SwiftUI
import OpenSourceOrthoLiteKit

/// `@main` entry for the iOS lite app. Lives in the Xcode app target (not built
/// by SwiftPM) and depends on the `OpenSourceOrthoLiteKit` library for all
/// engine/contract logic. See ../README.md for wiring this into Xcode.
@main
struct OpenSourceOrthoLiteApp: App {
    @StateObject private var model = LiteFlowViewModel(client: EngineClient())

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(model)
        }
    }
}
