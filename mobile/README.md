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

The full app is already mostly a *thin client*: the [`ui/`](../ui) web prototype
does not reimplement the Python planning engine (see
[`ui/README.md`](../ui/README.md), "Engine is the single source of truth"). The
mobile lite apps follow that rule for full-fidelity work, with one deliberate
exception: if the engine is unreachable and every selected generation input is
an STL, mobile may synthesize a **limited STL-only review artifact** on-device.
That fallback is plainly labeled and routes mesh-backed edits, CBCT/DICOM,
segmentation, and print-critical review back to the browser/full engine.

Because the engine is the single source of truth, the two apps do not need to
share UI code to stay consistent; they only need to agree on the **wire
contract**. That contract is written down once in
[`API_CONTRACT.md`](API_CONTRACT.md) and both apps target it. This keeps each
app idiomatically native (SwiftUI / Compose) without a cross-platform runtime,
matching the repo's no-heavy-framework, auditable, offline-leaning posture.

## The lite flow

Both apps implement the same four-step phone flow. The full clinician workspace
(records, caps editor, staged-movement table, plan versions) is intentionally
**out of scope** for lite, but the phone scaffold now mirrors the expected user
path.

1. **Upload files** - STL scans for mobile preview/review, CBCT/DICOM and photos
   as attached context, plus browser/full-engine JSON reviews/packages imported
   for on-device storage and sharing.
2. **Teeth + time** - show a 3D preview surface, stage scrubber, and the action
   that posts a plan-shaped payload to the engine's `POST /api/generate-plan`.
   If the engine is offline and the selected records are STL-only, the app builds
   a limited on-device review instead of blocking the user completely.
3. **Review** - the engine runs deterministic generation + named correctness
   checks and returns a `CONSISTENT` / `ISSUES` verdict (never "safe"/"approved").
   An optional model review is consent-gated and lint-filtered server-side.
4. **Print + send** - prepare the generated package for clinician review, lab
   handoff, or 3D-printer export.

```
[Upload files] -> [Teeth + time] -> [Review] -> [Print + send]
```

## Safety boundary (applies to mobile exactly as to the rest of the repo)

OpenSource Ortho is **not** a medical device, an Invisalign clone, a clinical
approval tool, an autonomous treatment planner, or complete treatment-planning
software. The mobile lite apps must carry the same disclaimers and must never
present a plan, generated package, or appliance as safe, approved, cleared, or
ready for treatment or physical use. The engine's verdict is `CONSISTENT` or
`ISSUES` only. Model-generated text is untrusted and is lint-gated by the engine
before it ever reaches the device. See [`docs/SAFETY.md`](../docs/SAFETY.md).

CBCT/DICOM can be attached on mobile, but real root/bone-aware checks require
local DICOM ingestion, volume viewing, STL-to-CBCT registration, reviewed
anatomy, and quality metrics. Users should run that work in the browser/full
engine, then import the resulting JSON review/package into mobile if they want
the plan and review available on the device.

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

## Browser handoff and device storage

The mobile apps can import JSON produced by the local browser/Python workspace
and keep it as an opaque stored review. Mobile does not edit those browser
artifacts; it preserves them for review, export, sharing, and device-side
handoff. This gives users a phone-friendly copy of work created with the full
geometry stack without creating a second mobile planning engine.

## Layout

```
mobile/
  README.md            <- you are here
  API_CONTRACT.md      <- the single HTTP/JSON contract both apps target
  .gitignore           <- mobile build artifacts (Xcode/Gradle)
  ios/                 <- Swift / SwiftUI lite app
  android/             <- Kotlin / Jetpack Compose lite app
```
