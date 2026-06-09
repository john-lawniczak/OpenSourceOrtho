# OpenSource Ortho - Android (Lite)

Native **Kotlin + Jetpack Compose** lite client. A thin client over the Python
engine; it renders what the engine returns and never synthesizes a plan
on-device. See the shared [`../README.md`](../README.md) and the wire contract in
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
      LiteFlow.kt                flow steps + minimal plan builder
      SafetyText.kt              verdict labels (disclaimer text in strings.xml)
      LiteFlowViewModel.kt       StateFlow UI state, delegates to the client
      MainActivity.kt            Compose entry + safety banner
      LiteScreens.kt             Upload / Generate / Review / Progression
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

## Run against the engine

Start the engine on the host: `python3 -m orthoplan.server` (binds
`127.0.0.1:8000`). The Android emulator reaches the host loopback at
`http://10.0.2.2:8000` - that is `EngineConfig.EMULATOR` (the default). Cleartext
HTTP is allowed only for the dev hosts listed in
`res/xml/network_security_config.xml`; a production build must use an `https://`
engine.

## What still has to be built (lite v1 -> shippable)

- **STL file picker**: replace the stub in `UploadScreen` with the Storage Access
  Framework (`ACTION_OPEN_DOCUMENT`), and register bytes with the engine mesh
  workspace.
- **3D progression renderer**: an OpenGL ES / Filament view in `ProgressionScreen`
  that animates `plan.stages` over time, mirroring `ui/viewer3d.js`. Mesh bytes
  come from `GET /api/mesh/<id>`; fall back to schematic proxy teeth when absent.
- **Production engine URL** over `https://`.
- **Optional model review consent** UI before setting `share_acknowledged`.

## Safety

The non-dismissible banner (`R.string.safety_disclaimer`) and `CONSISTENT`/`ISSUES`
verdict labels are mandatory. Never present a plan, generated package, printed
model, aligner, or other appliance as safe, approved, cleared, complete, suitable,
or ready for treatment or physical use. Any physical use is the user's own
responsibility and risk. See [`../../docs/SAFETY.md`](../../docs/SAFETY.md).
