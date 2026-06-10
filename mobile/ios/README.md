# OpenSource Ortho - iOS (Lite)

Native **SwiftUI** lite client. A thin client over the Python engine; it renders
what the engine returns and never synthesizes a plan on-device. See the shared
[`../README.md`](../README.md) and the wire contract in
[`../API_CONTRACT.md`](../API_CONTRACT.md).

## Layout

```
ios/
  OpenSourceOrthoLite.xcodeproj      generated app project for Simulator/device
  project.yml                        XcodeGen source for the app project
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
    Info.plist                        app metadata + version placeholders
    AppIdentity.swift                 bundle version/build reader for About
    LiteFlowViewModel.swift           view state, delegates to the kit
    RootView.swift                    nav + non-dismissible safety banner
    Screens.swift                     Upload / Teeth + Time / Review / Print + Send
    SettingsView.swift                Settings / About / Glossary / Teeth map
```

## Build the core (no Xcode)

The logic library builds and tests headless:

```bash
cd mobile/ios
swift build
swift test
```

## Run the app

Open `OpenSourceOrthoLite.xcodeproj`, select the `OpenSourceOrthoLite` scheme,
choose an iPhone Simulator, and press Run. If the project needs to be regenerated:

```bash
cd mobile/ios
xcodegen generate
```

The app target keeps `CFBundleShortVersionString` as `$(MARKETING_VERSION)` and
`CFBundleVersion` as `$(CURRENT_PROJECT_VERSION)`. `SettingsView` displays those
bundle values as `Version 1.5 (5)`.

Start the engine before generating a plan: `python3 -m orthoplan.server` (host
loopback `127.0.0.1:8000`, which the Simulator reaches directly - see
`EngineConfig.simulator`).

## What still has to be built (lite v1 -> shippable)

- **Mesh registration**: `UploadView` uses `.fileImporter` for DICOM/ZIP, `.stl`,
  and images; the next step is uploading/registering bytes with the engine mesh
  workspace instead of sending metadata only.
- **Mesh-backed 3D renderer**: `TeethAndTimeView` has an interactive SceneKit
  preview; replace the schematic teeth with `plan.stages` and mesh bytes from
  `GET /api/mesh/<id>`.
- **Destination-specific print/send handoff**: `PrintAndSendView` writes a JSON
  package and exposes the system share sheet; add lab/printer profiles as those
  destinations are chosen.
- **Production engine URL** over `https://`, plus App Transport Security set so
  cleartext is allowed only for the local dev hosts.
- **Optional model review consent** UI before setting `share_acknowledged`.

## Safety

The non-dismissible banner (`SafetyText.disclaimer`) and `CONSISTENT`/`ISSUES`
verdict labels are mandatory. Never present a plan, generated package, printed
model, aligner, or other appliance as safe, approved, cleared, complete, suitable,
or ready for treatment or physical use. Any physical use is the user's own
responsibility and risk. See [`../../docs/SAFETY.md`](../../docs/SAFETY.md).
