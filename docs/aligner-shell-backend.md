# Scope: robust aligner-shell backend

> Status: **Phase 1 shipped (selection + fail-closed fallback + manifest
> identity); robust offset not yet validated.** A `shell_backend` setting selects
> between the always-on pure-Python shell and an optional `robust` path
> (`aligner_shell_robust.py`) behind the `mesh-processing` extra (Open3D). When
> Open3D is absent the export falls back to pure-Python **and records the
> downgrade** in the manifest; it never silently changes geometry. The robust path
> currently does mesh **repair** (merge near-duplicate vertices, drop degenerate
> triangles, remove non-manifold edges, orient consistently, recompute robust
> normals) and then reuses the shared `assemble_shell` offset. A true
> boolean/signed-distance (Minkowski) offset is the next slice.
>
> Educational tooling only — generating shell geometry is never a diagnosis, a
> treatment decision, or a statement that printing, fit, materials, or physical
> use are safe. Those remain the user's own responsibility and risk.

## Why

The pure-Python shell (`aligner_shell.py`) offsets the reviewed crown surface
along vertex normals and stitches a rim. It is deterministic, dependency-free,
and good enough for clean reviewed crowns, but it assumes consistent outward
winding and cannot repair messy input or produce a true constant-distance offset
at high-curvature concavities (where a normal-offset shell can self-intersect).
That vertex-normal approximation is the main thing keeping Track 1 below 9/10.

## The contract to preserve

Both backends route through one shared function so QA stays identical:

- `assemble_shell(verts, faces, *, thickness_mm, minimum_printable_feature_mm,
  trim, xy_compensation_mm, z_compensation_mm, dropped, skinny)` in
  `aligner_shell.py` owns the offset, rim stitching, printer compensation, and the
  `ShellStats` QA block (watertight, connected components, rim closure, real
  triangle-triangle self-intersection count, nonmanifold edges, thickness
  distribution, clearance).
- A backend only has to turn raw triangles into `(verts, faces, dropped, skinny)`.
  Pure-Python uses `clean_triangles` + `index_mesh`; the robust path uses Open3D
  repair (`aligner_shell_robust._repair_mesh`).

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

## What "validated" (and a 9/10) would require

- Open3D installed in a test environment so the robust path actually executes.
- Fixtures comparing robust vs pure-Python QA on messy non-PHI meshes (holes,
  islands, slivers, inverted winding, nonmanifold edges) — see the Phase 9
  follow-up in `TODO.md`.
- A true boolean/signed-distance offset (not just repair) so the shell is a real
  constant-distance wall rather than a normal-offset approximation.

Until the robust path is validated against the pure-Python path on a messy
corpus, Track 1 stays at ~8/10: the architecture and fail-closed fallback exist,
but the robust offset is not yet proven.
