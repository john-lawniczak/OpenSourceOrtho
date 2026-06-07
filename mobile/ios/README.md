# OpenSource Ortho - iOS (Lite)

Native **SwiftUI** lite client. A thin client over the Python engine; it renders
what the engine returns and never synthesizes a plan on-device. See the shared
[`../README.md`](../README.md) and the wire contract in
[`../API_CONTRACT.md`](../API_CONTRACT.md).

## Layout

```
ios/
  Package.swift                       SwiftPM library + tests for the core
  Sources/OpenSourceOrthoLiteKit/     engine logic (no UI) - compiles & tests headless
    EngineConfig.swift                engine base URL (one place to change)
    EngineModels.swift                Codable mirrors of the contract subset
    AnyCodable.swift                  type-erased JSON for the opaque plan payload
    EngineClient.swift                async HTTP client for the lite endpoints
    LiteFlow.swift                    flow steps + minimal plan builder
    SafetyText.swift                  standing disclaimer + verdict labels
  Tests/OpenSourceOrthoLiteKitTests/  XCTest for the core
  App/                                SwiftUI app target sources (added in Xcode)
    OpenSourceOrthoLiteApp.swift      @main entry
    LiteFlowViewModel.swift           view state, delegates to the kit
    RootView.swift                    nav + non-dismissible safety banner
    Screens.swift                     Upload / Generate / Review / Progression
```

## Build the core (no Xcode)

The logic library builds and tests headless:

```bash
cd mobile/ios
swift build
swift test
```

## Run the app

The SwiftUI `App/` sources need an Xcode app target (a SwiftUI `@main` entry
cannot be built by SwiftPM). One-time setup:

1. Open Xcode -> **New Project -> iOS App** (SwiftUI), name `OpenSourceOrthoLite`.
2. Remove the generated `ContentView.swift`/`App.swift`; add the files under
   `App/` to the app target.
3. Add this package as a **local Swift Package** dependency and link
   `OpenSourceOrthoLiteKit` to the app target.
4. Start the engine: `python3 -m orthoplan.server` (host loopback `127.0.0.1:8000`,
   which the Simulator reaches directly - see `EngineConfig.simulator`).
5. Run on the iOS Simulator.

> The generated `.xcodeproj` is intentionally **not** committed - it is
> machine/Xcode-version specific and noisy to review. The committed Swift sources
> are the durable scaffolding.

## What still has to be built (lite v1 -> shippable)

- **STL file picker**: replace the stub in `UploadView` with `.fileImporter`
  for `.stl`, and register bytes with the engine mesh workspace.
- **3D progression renderer**: a SceneKit/Metal view in `ProgressionView` that
  animates `plan.stages` over time, mirroring `ui/viewer3d.js`. Mesh bytes come
  from `GET /api/mesh/<id>`; fall back to schematic proxy teeth when absent.
- **Production engine URL** over `https://`, plus App Transport Security set so
  cleartext is allowed only for the local dev hosts.
- **Optional model review consent** UI before setting `share_acknowledged`.

## Safety

The non-dismissible banner (`SafetyText.disclaimer`) and `CONSISTENT`/`ISSUES`
verdict labels are mandatory. Never present a plan as safe, approved, cleared, or
ready for treatment. See [`../../docs/SAFETY.md`](../../docs/SAFETY.md).
