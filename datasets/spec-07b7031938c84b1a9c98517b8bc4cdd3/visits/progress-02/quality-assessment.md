# Week 18 damaged-model mesh evaluation

**USER_ONE contributed data — both stone models chipped.**

The contributor confirms that both hardened stone models were chipped and poorly made. The defects are not a reflection of the actual teeth. This is contributor-reported provenance, not a diagnosis inferred from the meshes. Exact affected regions and chip timing are not separately documented.

## Measured file properties

| Check | Upper | Lower |
| --- | ---: | ---: |
| Triangles | 828,960 | 461,345 |
| Unique vertices (exact coordinates) | 416,067 | 231,837 |
| Zero-area triangles | 26 | 16 |
| Duplicate triangles | 0 | 0 |
| Boundary edges | 3,246 | 2,355 |
| Edges incident to more than two faces | 26 | 16 |
| Connected components (vertex connectivity) | 1 | 1 |
| Non-finite coordinates | 0 | 0 |

Both original SHA-256 hashes match the manifests. Original STL bytes remain unchanged. Boundary edges mean these surfaces are not closed. No repairs, smoothing, hole filling, scaling, or registration were applied. Triangle count is mesh density, not evidence of accuracy. All extents are in unverified source units, not verified millimeters.

## Advisory interpretation

The following model-generated observations passed `lint_finding()` before export and remain unverified; the gate checks language, not anatomical correctness.

**Surface appearance is unverified.** The upper rendering appears rougher and more interrupted, with visible openings; the lower appears smoother but also contains broad sheet-like surfaces around the arch. These visual observations do not localize the reported chips or distinguish model-making defects from capture or reconstruction artifacts.

**Topology does not establish anatomical fidelity.** Both meshes have open boundary edges, zero-area triangles, and edges with more than two incident faces. Open boundaries can include intentional scan margins. These counts do not measure chip severity, prove the shapes match teeth, or rank scanner accuracy. A closed or repaired mesh would not recover missing original anatomy.

**Limit reuse to damaged-model experiments.** Retain this pair for mesh-import, rendering, robustness, and defect-handling experiments with the damage label attached. Exclude it from reference tooth geometry and quantitative tooth-movement or tracking comparisons unless affected regions are independently mapped and the required geometry, scale, and registration are validated. Do not interpret defects as tooth damage or treatment change.

## Evidence and reproduction

- [Original-surface views](mesh-views.png): every triangle, independently fitted panels, no anatomical registration.
- [Machine-readable topology inventory](mesh-quality.json): exact-coordinate method and unassessed properties.
- [Damage provenance](source-metadata.json): both arches; contributor distinguishes model defects from the actual teeth.
- [Linted advisory findings](quality-findings.json).

From the repository root, with NumPy and Matplotlib installed in the virtual environment:

```bash
MPLCONFIGDIR=/private/tmp/ortho-week18-matplotlib .venv/bin/python \
  datasets/spec-07b7031938c84b1a9c98517b8bc4cdd3/visits/progress-02/evaluate_meshes.py
```

The script regenerates the measured inventory and figure. Self-intersections, vertex manifoldness, winding, scanner accuracy, true tooth shape, physical scale, bite relationship, and registration are not evaluated. Rendering is an approximate depth-sorted orthographic inspection, not a surface-error measurement.
