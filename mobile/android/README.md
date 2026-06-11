# OpenSource Ortho - Android (Lite)

Native **Kotlin + Jetpack Compose** lite client. It uses the Python engine for
full-fidelity work and can synthesize only a clearly labeled STL-only review when
that engine is offline. CBCT/DICOM, segmentation, mesh-backed edits, and
print-critical exports remain browser/full-engine workflows. See the shared
[`../README.md`](../README.md) and the wire contract in
[`../API_CONTRACT.md`](../API_CONTRACT.md).

## Layout

```
android/
  settings.gradle.kts            module + repo config
  build.gradle.kts               root plugin versions
  gradle.properties
  app/
    build.gradle.kts             :app module (Compose, kotlinx.serialization)
    src/main/AndroidManifest.xml
    src/main/res/                strings (safety disclaimer), theme, ATS config
    src/main/kotlin/com/opensourceortho/lite/
      EngineConfig.kt            engine base URL (one place to change)
      EngineModels.kt            @Serializable mirrors of the contract subset
      EngineClient.kt            coroutine HTTP client for the lite endpoints
      LiteFlow.kt                flow steps, minimal plan builder, STL fallback
      SafetyText.kt              verdict labels (disclaimer text in strings.xml)
      LiteFlowViewModel.kt       StateFlow UI state, delegates to the client
      MainActivity.kt            Compose entry + safety banner
      LiteScreens.kt             Upload / Teeth + Time / Review / Print + Send / Settings
    src/test/kotlin/...          JVM unit tests for the core
```

## Build & test

The gradle **wrapper jar is intentionally not committed** (it is a binary).
Generate it once with a local Gradle (8.7+), then use the wrapper as usual:

```bash
cd mobile/android
gradle wrapper --gradle-version 8.9   # one-time: creates ./gradlew + wrapper jar
./gradlew testDebugUnitTest           # run JVM unit tests
./gradlew assembleDebug               # build the debug APK
```

Open the `mobile/android/` folder in Android Studio to run on an emulator.
The Settings About card reads `BuildConfig.VERSION_NAME` and
`BuildConfig.VERSION_CODE`; keep version metadata in `app/build.gradle.kts`.

## Run against the engine

Start the engine on the host: `python3 -m orthoplan.server` (binds
`127.0.0.1:8000`). The Android emulator reaches the host loopback at
`http://10.0.2.2:8000` - that is `EngineConfig.EMULATOR` (the default). Cleartext
HTTP is allowed only for the dev hosts listed in
`res/xml/network_security_config.xml`; a production build must use an `https://`
engine.

## What still has to be built (lite v1 -> shippable)

- **Mesh registration**: `UploadScreen` uses the Storage Access Framework for
  `.stl` files, CBCT/DICOM attachments, photos from local/cloud providers, and
  browser-generated JSON reviews/packages; the next step is uploading/registering
  STL bytes with the engine mesh workspace instead of sending metadata only.
- **Persistent review library**: browser JSON can be imported and included in
  the exported mobile package; add durable app storage and deletion/rename UI.
- **Per-tooth 3D renderer**: `TeethAndTimeScreen` now renders a projected native
  preview from selected STL geometry when URI access is available. Replace it
  with a Filament/OpenGL renderer backed by segmented per-tooth meshes from
  `GET /api/mesh/<id>` and engine stage transforms.
- **Destination-specific print/send handoff**: `PrintAndSendScreen` writes a JSON
  package, supports Android document export, opens Sharesheet targets, and opens
  the platform print dialog; add lab/printer profiles as those destinations are
  chosen.
- **Production engine URL** over `https://`.
- **Optional model review consent** UI before setting `share_acknowledged`.
- **Browser handoff links** for opening the same case in the local/hosted
  browser workspace when CBCT/DICOM or plan editing is needed.

## Safety

The non-dismissible banner (`R.string.safety_disclaimer`) and `CONSISTENT`/`ISSUES`
verdict labels are mandatory. Never present a plan, generated package, printed
model, aligner, or other appliance as safe, approved, cleared, complete, suitable,
or ready for treatment or physical use. Any physical use is the user's own
responsibility and risk. See [`../../docs/SAFETY.md`](../../docs/SAFETY.md).
