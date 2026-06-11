# Mobile Lite - Engine API Contract

The single source of truth for what the iOS and Android lite apps send to and
expect from the Python engine. Both native clients implement *this* document, not
each other. If the engine's shape changes, update this file and both apps.

The authoritative server implementation is [`orthoplan/server.py`](../orthoplan/server.py)
(routing) and [`orthoplan/generation.py`](../orthoplan/generation.py) /
[`orthoplan/api.py`](../orthoplan/api.py) (payloads). This file is a mobile-facing
**subset** - lite uses only the endpoints below.

All responses are JSON objects. Every endpoint returns either:

- `{ "ok": true,  ... }` - success, with the fields documented per endpoint, or
- `{ "ok": false, "errors": ["..."] }` - validation/usage error (HTTP 200/4xx).

Clients must treat any non-`ok` body, transport error, or unreachable host as
"engine offline / request rejected" and surface that plainly. The only allowed
mobile fallback is the explicitly labeled STL-only review described below; it is
not a second full planning engine.

## Base URL

| Context                 | Base URL                  |
|-------------------------|---------------------------|
| iOS Simulator           | `http://127.0.0.1:8000`   |
| Android emulator        | `http://10.0.2.2:8000`    |
| Production (future)     | `https://<your-engine>`   |

Cleartext HTTP is allowed for the two local dev hosts only.

---

## 1. `POST /api/generate-plan` - the core lite call

Primary endpoint for the lite flow. Request body (subset of `GenerateRequest`):

```jsonc
{
  "plan": { /* plan-shaped object (TreatmentPlan). Lite sends a minimal plan
               carrying the uploaded scan metadata + default settings. */ },
  "acknowledge_educational": true,   // user accepted the educational-fallback banner
  "provider": "local",               // "local" keeps everything on the engine host
  "share_acknowledged": false,       // egress consent for an EXTERNAL model review
  "notes": null                       // optional free-text focus for the review step
}
```

Lite defaults to `provider: "local"` and `share_acknowledged: false`, so no data
leaves the engine host. An external model review is only attempted when the user
explicitly opts in (a future lite setting); without consent the engine returns a
skipped/offline review step rather than calling out.

Success response (subset of fields the lite UI renders):

```jsonc
{
  "ok": true,
  "source": "authored | landmark-derived | geometry-derived | educational-synthetic | none",
  "requires_acknowledgement": false,
  "warnings": ["..."],
  "steps":   [ { "name": "...", "status": "ok|warning|skipped", "detail": "..." } ],
  "checks":  [ { /* named correctness checks */ } ],
  "correctness": { "verdict": "CONSISTENT | ISSUES", "...": "metrics" },
  "stage_count": 12,
  "space": { "discrepancy_mm": 0.0, "residual_mm": 0.0,
             "ipr_count": 0, "attachment_count": 0 },
  "timeline": {
    "stage_count": 12,
    "wear_interval_days": 14,
    "projected_duration_days": 168,
    "projected_duration_weeks": 24.0,
    "caveat": "Projection excludes refinements, compliance variation, ..."
  },
  "deterministic_findings": [ { /* lint-gated findings */ } ],
  "advisory_findings":      [ { /* model review, already lint-gated server-side */ } ],
  "plan":  { /* full generated plan, incl. stages used for progression rendering */ },
  "caveat": "Plan generation is deterministic ... NOT that it is safe/approved ..."
}
```

Lite screens map to these fields:

- **Review screen** -> `correctness.verdict`, `steps`, `deterministic_findings`,
  `advisory_findings`, `warnings`, and the standing `caveat`.
- **Progression screen** -> `timeline` (duration + caveat) and `plan.stages`
  (per-stage tooth movement to animate over time).

> `verdict` is `CONSISTENT` or `ISSUES`. Never render it as "safe", "approved",
> "cleared", or "ready". Always show `caveat`.

### STL-only on-device fallback

If `POST /api/generate-plan` is unreachable and every selected input is an STL,
the native app may return a local `GeneratePlanResponse` with:

- `source: "mobile-stl-best-effort"`
- `correctness.verdict: "CONSISTENT"` only as an internal consistency label
- warnings that name the browser/full engine as required for segmentation,
  mesh-backed edits, CBCT/DICOM, and print-critical review
- an empty/opaque staged plan suitable for mobile display and export, not for
  clinical or manufacturing reliance

The fallback must not run for CBCT/DICOM, photos, mixed modalities, or any case
that implies root/bone-aware review.

---

## 2. `POST /api/evaluate` - re-evaluate an existing plan (optional)

Same engine, used if the user tweaks a value on-device. Body: a plan-shaped
object. Returns the engine's findings, data gaps, timeline, and stage progress
frames. Lite may skip this initially and rely on `generate-plan` only.

---

## 3. `GET /api/mesh/<mesh_asset_id>` - registered local mesh bytes

Serves an STL/mesh registered in the engine's local mesh workspace, for the 3D
preview. Returns raw bytes (`model/stl` / `application/octet-stream`) or
`{ "ok": false }` 404. Plan JSON never carries mesh bytes; only registered asset
ids are referenced. If no mesh link is available, the app falls back to schematic
proxy teeth (same rule as the web viewer).

---

## 4. `POST /api/chat` - scoped Plan AI (optional, out of lite v1)

Consent-gated advisory chat about the current plan. Not part of the lite v1 flow;
documented here so the apps can add it later without re-deriving the contract.

---

## Error and offline handling (both apps)

| Situation                       | App behavior                                        |
|---------------------------------|-----------------------------------------------------|
| Host unreachable / timeout with STL-only inputs | Limited `mobile-stl-best-effort` response, clearly caveated |
| Host unreachable / timeout with CBCT/DICOM or mixed inputs | "Engine offline" state; use browser/full engine |
| `{ "ok": false, "errors": [] }` | Show the returned error strings verbatim            |
| Missing `caveat`                | Still show the standing safety disclaimer           |
| `verdict == "ISSUES"`           | Surface findings; never imply the plan is fine      |

## Browser review import

Mobile may import JSON files produced by the browser/Python workspace and store
them as opaque review artifacts. These imports are for on-device viewing,
sharing, and export only. Plan changes, CBCT/DICOM work, STL registration,
segmentation, and mesh-backed print package generation stay in the browser/full
engine.

## Standing disclaimer string

Both apps embed this exact wording (kept in sync with the engine `caveat`):

> OpenSource Ortho is a clear-aligner planning safety playground and research
> toolkit. The current build is not distributed as a medical device, is not
> complete treatment-planning software, and does not diagnose, treat, approve
> treatment, or authorize physical use. A `CONSISTENT` verdict means the staging
> is internally consistent with the configured caps and controls - not that it is
> safe, approved, or clinically appropriate. Always consult a licensed dental
> professional; any physical use is your own responsibility and risk.
