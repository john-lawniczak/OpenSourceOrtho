# Scope: bite registration (opposing-arch occlusal frame)

> Status: **Registration core + occlusal grid + the proximity overlay shipped.**
> `POST /api/occlusion` registers a scan pair and returns a classified proximity
> map the 3D viewer paints red/amber/green. The 3D scale reference that also builds
> on this is NOT yet wired.
>
> Educational, on-device visualization geometry only. This computes an APPROXIMATE
> occlusal *alignment* for review; it is never a measured bite, an occlusal-force
> map, a diagnosis, or a statement that a bite is correct, healthy, or complete.

## Why

The 3D viewer currently shows a **schematic** bite: the maxillary arch is raised
and the mandibular lowered by a fixed gap for visibility, with amplified curvature.
That is fine for reading the layout, but it discards the true spatial relationship
between the arches, so two things are impossible to build on top of it:

- a **proximity overlay** (the red/yellow/green "where do the arches meet" map), and
- a trustworthy **mm scale reference**, because the schematic layout is not at true
  scale.

Both need the two arches expressed in **one real metric frame** - a bite
registration. This is that substrate.

## The honest core: trust the scanner, estimate only when forced

A real intraoral export (e.g. iTero/OrthoCAD) registers the upper and lower arches
into a single bite frame using the scanner's **buccal-bite capture**. We confirmed
this on the bundled `canonical-orthocad-001` scans: both arches share x/y centring
(midline at x≈0) and interleave in z (upper down to ≈−1.5, lower up to ≈+3.5) - they
are already occluding in one frame.

So `register_bite` (`orthoplan/occlusion/registration.py`) has two modes:

- **`as-scanned`** - the arches already occlude (shared occlusal-plane footprint,
  biting surfaces within an occlusion band). We TRUST the scanner's registration
  (identity transform) and only **measure** it. This is truthful: the real bite came
  from the scanner's bite scan, not from us.
- **`estimated`** - the arches arrive in separate/arbitrary frames. We fall back to a
  plain, **clearly flagged (`approximate=True`)** alignment: match occlusal-plane
  centroids, then bring the biting surfaces to first contact. Two *separate* arch
  scans cannot reveal the true bite (that is exactly what a bite scan is for), so
  this mode exists only to make the pair viewable, never to assert the bite.

`unavailable` is returned when an arch is missing or the arches share no footprint
even after alignment.

## The shared substrate: the occlusal grid

`orthoplan/occlusion/grid.py` buckets both arches' crown surfaces into a common
occlusal-plane (xy) grid and records, per cell, the **biting-surface height** of
each arch - the upper arch's lowest `z` (faces down) and the lower arch's highest
`z` (faces up), since `+z` is occlusal-superior (see `model.geometry`). The per-cell
signed clearance `upper_bottom − lower_top` is the one signal everything reads:

- `> 0` vertical clearance (gap) · `~ 0` contact · `< 0` overlap / interpenetration.

It is pure list math, O(n) over vertices, and dependency-free. `register_bite`
derives its metrics from it (`occlusal_gap_mm`, `interpenetration_mm`,
`contact_fraction`, `coverage`, `midline_offset_mm`, `extent_mm`, `confidence`).

## Measurement (how we prove it works)

`occlusion-registration-accuracy` in `orthoplan/validation/occlusion_cases.py` (run
via `run_measurement_lab`) builds an opposing arch pair with a **known** occlusal
gap and midline offset (`validation/occlusion_truth.py`) and asserts the
registration recovers them as `as-scanned`, with high coverage and no invented
interpenetration. `tests/test_occlusion_registration.py` additionally pins the
estimated-fallback path, the unavailable guard, the units flag, and that the real
bundled scans register `as-scanned`.

Known coarse-grid limitation (documented, not a bug): at the ~0.9 mm grid cell,
interdigitating cusps and fissures inside one cell can read as a few mm of apparent
interpenetration on real scans. That is acceptable for a registration indicator; the
**proximity overlay** will need a finer, nearest-surface measure for true contact
detail (see next steps).

## What this unblocks

- [x] **Proximity overlay** (shipped): `orthoplan/occlusion/proximity.py` classifies
      each shared occlusal-grid cell into `contact` / `near` / `clearance` bands
      (clearance `<= 0.5` / `<= 1.5` / `> 1.5` scan units) and `POST /api/occlusion`
      (`proximity_api.py`) returns the located cells. The 3D viewer
      (`viewer3d.js` `loadProximity`) paints them red/amber/green between the
      registered arches, toggled by the "Bite proximity" control with a legend. It
      is painted ONLY for an `as-scanned` registration (`aligned_to_scan`): an
      estimated alignment moved the lower arch, so its coordinates would not match
      the rendered scans. Framed as geometric proximity, NOT bite force. NOTE: still
      at the coarse ~0.9 mm grid cell - a future pass may use nearest-surface
      distance for finer contact detail.
- [x] **3D scale reference** (shipped): a "Scale" viewer toggle draws a labelled
      10 mm reference bar beside a loaded scan (`viewer3d.js` `updateScaleBar`), with
      a status strip reporting the scan's measured W×H×D extent. It is pure viewer
      geometry from the scan's true-scale bounding box (so it works for any loaded
      scan, not only the occlusion path) and is gated on confirmed mm units - the
      status tells the user to confirm units otherwise. Text logic in `ui/scale.js`
      (unit-tested); honesty: the scan geometry is true-scale, only tooth movement is
      exaggerated.
- [x] **Viewer integration** (shipped): a "Registered bite" viewer toggle moves the
      lower arch into the registered occlusal frame using the registration's
      `lower_offset` (now returned by `/api/occlusion` and mapped to viewer axes by
      `proximity.js` `registeredOffsetForViewer`; applied by `viewer3d.js`
      `setArchRegistration`). It only changes **estimated** (separate-frame) pairs:
      an as-scanned export already occludes, so the toggle is a no-op there and the
      status says so. NOTE: the proximity overlay is still painted only for
      as-scanned pairs; painting it in the registered-bite (estimated) view is a
      further step. There is no bundled separate-frame fixture, so this path is
      exercised by `register_bite` unit tests + the pure offset-mapping helper tests,
      not end-to-end in the viewer.
- [x] **API seam** (closed — no separate work needed): **`/api/occlusion` IS the
      seam.** It already returns the full registration metrics (`mode`,
      `occlusal_gap_mm`, `interpenetration_mm`, `contact_fraction`, `coverage`,
      `midline_offset_mm`, `extent_mm`, `lower_offset`) for the only consumer today
      (the viewer). It is deliberately NOT folded into `evaluate`/`segment`:
      `evaluate_plan` takes a `TreatmentPlan` (no raw upper+lower arch pair) and
      `segment_payload` takes one arch at a time, so neither has the inputs
      registration needs; and embedding occlusion in the plan-evaluation response
      would blur the non-device boundary (it would read as "the plan includes an
      occlusal analysis"). Revisit only when a concrete server-side consumer appears
      — e.g. a report/print-package that embeds bite metrics, or a CLI/headless
      caller wrapping `register_bite`. **A local-AI chat explanation is a valid such
      consumer, but it would CONSUME this endpoint's output** (passed into the chat
      context the browser already holds), not require a new `evaluate`/`segment`
      field — and it must EXPLAIN the geometric numbers educationally, never
      *evaluate/diagnose the patient's bite* (see Risks).

## Constraints honoured

- Dependency-free, deterministic, on-device (scan bytes never leave the machine).
- No new runtime dependency; pure list math, no numpy in the core path.
- Safety boundary: approximate alignment for review only - not a measured bite, not
  occlusal analysis, not a diagnosis.
