# OpenSource Ortho - Mobile (Lite)

Scaffolding for the **lite** mobile builds of OpenSource Ortho: a focused subset
of the full web/desktop workspace, built as **two native apps developed in
parallel**.

| Platform | Directory       | UI toolkit          | Status      |
|----------|-----------------|---------------------|-------------|
| iOS      | [`ios/`](ios/)         | Swift / SwiftUI     | scaffolding |
| Android  | [`android/`](android/) | Kotlin / Compose    | scaffolding |

> **This is scaffolding, not a shippable app.** The flow, screens, networking
> client, and data contract are stubbed so iOS and Android can grow in parallel.
> Neither target is wired for store release. See each platform README for what
> still has to be built before a real build.

## Why two native projects (not a shared cross-platform codebase)

The full app is already a *thin client*: the [`ui/`](../ui) web prototype computes
nothing on its own and renders exactly what the Python engine returns over HTTP
(see [`ui/README.md`](../ui/README.md), "Engine is the single source of truth").
The mobile lite apps follow the same rule - they are thin native clients over the
same HTTP engine.

Because the engine is the single source of truth, the two apps do not need to
share UI code to stay consistent; they only need to agree on the **wire
contract**. That contract is written down once in
[`API_CONTRACT.md`](API_CONTRACT.md) and both apps target it. This keeps each
app idiomatically native (SwiftUI / Compose) without a cross-platform runtime,
matching the repo's no-heavy-framework, auditable, offline-leaning posture.

## The lite flow

Both apps implement the same four-step STL surface-planning flow. The full clinician workspace
(records, caps editor, staged-movement table, plan versions, print export) is
intentionally **out of scope** for lite.

1. **Upload** an STL scan (upper and/or lower arch) from the device.
2. **Generate Plan** - one tap. The app posts a plan-shaped payload to the
   engine's `POST /api/generate-plan`.
3. **Review** - the engine runs deterministic generation + named correctness
   checks and returns a `CONSISTENT` / `ISSUES` verdict (never "safe"/"approved").
   An optional model review is consent-gated and lint-filtered server-side.
4. **Progression** - render the staged progression and a 3D preview of tooth
   movement over time from the engine's timeline + stage frames.

```
[Upload STL] -> [Generate Plan] -> [Engine review + verdict] -> [Progression + 3D over time]
```

## Safety boundary (applies to mobile exactly as to the rest of the repo)

OpenSource Ortho is **not** a medical device, an Invisalign clone, a clinical
approval tool, or an autonomous treatment planner. The mobile lite apps must
carry the same disclaimers and must never present a plan as safe, approved,
cleared, or ready for treatment. The engine's verdict is `CONSISTENT` or
`ISSUES` only. Model-generated text is untrusted and is lint-gated by the engine
before it ever reaches the device. See [`docs/SAFETY.md`](../docs/SAFETY.md).

CBCT/DICOM support is part of the full product roadmap, not the lite scaffold.
The lite flow remains STL-only until the engine exposes local DICOM ingestion,
registration, and reviewed root/bone-aware planning contracts.

Each app ships a standing, non-dismissible disclaimer string sourced from
[`API_CONTRACT.md`](API_CONTRACT.md) so the wording stays consistent with the
engine's `caveat` field.

## Talking to the engine

During development the engine runs locally:

```bash
python3 -m orthoplan.server        # or: orthoplan serve  -> http://127.0.0.1:8000
```

- iOS Simulator reaches the host at `http://127.0.0.1:8000`.
- Android emulator reaches the host loopback at `http://10.0.2.2:8000`.

Each app centralizes this base URL in one config file (`Config.swift` /
`EngineConfig.kt`) so a real deployment only changes one constant. Cleartext
HTTP is permitted **only** for these local development hosts; a production build
must point at an `https://` engine.

## Layout

```
mobile/
  README.md            <- you are here
  API_CONTRACT.md      <- the single HTTP/JSON contract both apps target
  .gitignore           <- mobile build artifacts (Xcode/Gradle)
  ios/                 <- Swift / SwiftUI lite app
  android/             <- Kotlin / Jetpack Compose lite app
```
