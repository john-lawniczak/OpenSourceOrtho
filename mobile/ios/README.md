# OpenSource Ortho - iOS (Lite)

Native **SwiftUI** lite client. It uses the Python engine for full-fidelity work
and can synthesize only a clearly labeled STL-only review when that engine is
offline. CBCT/DICOM, segmentation, mesh-backed edits, and print-critical exports
remain browser/full-engine workflows. See the shared [`../README.md`](../README.md)
and the wire contract in
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
    LiteFlow.swift                    flow steps, minimal plan builder, STL fallback
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

- **Mesh registration**: `UploadView` accepts `.stl`, CBCT/DICOM attachments,
  photos from the library or Files/iCloud/Drive providers, and browser-generated
  JSON reviews/packages; the next step is uploading/registering STL bytes with
  the engine mesh workspace instead of sending metadata only.
- **Persistent review library**: browser JSON can be imported and included in
  the exported mobile package; add durable app storage and deletion/rename UI.
- **Per-tooth 3D renderer**: `TeethAndTimeView` now renders selected STL scan
  geometry in SceneKit when local bytes are available. The next step is replacing
  whole-arch STL preview with segmented per-tooth meshes from `GET /api/mesh/<id>`
  and rendering engine stage transforms on those meshes.
- **Destination-specific print/send handoff**: `PrintAndSendView` writes a JSON
  package and exposes the system share sheet; add lab/printer profiles as those
  destinations are chosen.
- **Production engine URL** over `https://`, plus App Transport Security set so
  cleartext is allowed only for the local dev hosts.
- **Optional model review consent** UI before setting `share_acknowledged`.
- **Browser handoff links** for opening the same case in the local/hosted
  browser workspace when CBCT/DICOM or plan editing is needed.

## Safety

The non-dismissible banner (`SafetyText.disclaimer`) and `CONSISTENT`/`ISSUES`
verdict labels are mandatory. Never present a plan, generated package, printed
model, aligner, or other appliance as safe, approved, cleared, complete, suitable,
or ready for treatment or physical use. Any physical use is the user's own
responsibility and risk. See [`../../docs/SAFETY.md`](../../docs/SAFETY.md).
