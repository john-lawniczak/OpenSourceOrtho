# Scope: robust aligner-shell backend

> Status: **Phase 9.2/9.3/9.4 software validation shipped.** A `shell_backend` setting selects
> between the always-on pure-Python shell and an optional `robust` path
> (`aligner_shell_robust.py`) behind the `mesh-processing` extra (Open3D). When
> Open3D is absent the export falls back to pure-Python **and records the
> downgrade** in the manifest; it never silently changes geometry. The robust path
> now does mesh **repair** (merge near-duplicate vertices, drop degenerate
> triangles, remove non-manifold edges, orient consistently, recompute robust
> normals), then uses Open3D distance queries to correct the outer surface toward
> the requested offset before the shared shell QA closes and evaluates the mesh.
> CI includes a dedicated Open3D lane for the robust backend tests.
>
> Educational tooling only — generating shell geometry is never a diagnosis, a
> treatment decision, or a statement that printing, fit, materials, or physical
> use are safe. Those remain the user's own responsibility and risk.

## Why

The pure-Python shell (`aligner_shell.py`) offsets the reviewed crown surface
along vertex normals and stitches a rim. It is deterministic, dependency-free,
and good enough for clean reviewed crowns, but it assumes consistent outward
winding and cannot repair messy input. The robust path keeps the same safety
contract while adding repair plus an Open3D distance-field correction pass so
the outer surface is checked against the requested wall distance.

## The contract to preserve

Both backends route through shared assembly/QA functions so QA stays identical:

- `assemble_shell(verts, faces, *, thickness_mm, minimum_printable_feature_mm,
  trim, xy_compensation_mm, z_compensation_mm, dropped, skinny)` in
  `aligner_shell.py` owns the offset, rim stitching, printer compensation, and the
  `ShellStats` QA block (watertight, connected components, rim closure, real
  triangle-triangle self-intersection count, nonmanifold edges, thickness
  distribution, clearance).
- `assemble_shell_surfaces(inner, outer, faces, ...)` owns rim stitching and QA
  when a backend has already computed inner/outer surfaces.
- A backend only has to prepare clean surfaces and pass them into the shared
  assembly/QA contract. Pure-Python uses `clean_triangles` + `index_mesh`; the
  robust path uses Open3D repair plus RaycastingScene distance queries
  (`aligner_shell_robust.py`).

## Selection and fail-closed behavior

`print_aligner.resolve_shell_backend(settings)` returns the resolved identity:

```
{ "requested": "robust"|"pure-python",
  "used":      "robust"|"pure-python",
  "available": <Open3D importable>,
  "fallback_reason": <str or None> }
```

- `shell_backend` defaults to `"pure-python"` (no behavior change, no extra).
- `"robust"` + Open3D installed → robust repair path.
- `"robust"` + Open3D missing → pure-Python shell, `fallback_reason` set. This is
  surfaced in the print-package manifest (`aligner_shells.backend`), the API
  response (`aligner_shell_backend`), and the print QA UI.

## Validation

- `.github/workflows/ci.yml` has a dedicated `mesh-processing` job that installs
  `.[dev,mesh-processing]` and runs the robust backend tests.
- `orthoplan.validation.shell_backend` compares robust vs pure-Python shell QA on
  messy synthetic fixtures and an independent full-arch generator, recording
  availability, validation-case count, thickness deltas, hash deltas,
  self-intersections, and nonmanifold edges in `orthoplan validation-benchmark`.
- The normal no-extra test lane remains fail-closed: if Open3D is unavailable,
  the validation report records that the robust comparison was skipped rather
  than implying it passed.

This moves the software geometry path toward the Track 1 target, but it still
does not model material behavior, thermoforming fit, printer calibration, or
physical-use safety.
