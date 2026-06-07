# Examples

Synthetic examples only. **Never commit patient data** (see [../docs/SAFETY.md](../docs/SAFETY.md)).

Everything here is fabricated. The checked-in plans are produced by
[`generate_examples.py`](generate_examples.py) with a fixed timestamp so they do
not churn between regenerations.

## Files

- `basic_plan.json` — a few stages, no scans, one movement that trips the linear cap.
- `segmented_plan.json` — a confirmed-units scan plus a per-tooth mesh with an
  approximate local frame. `tooth_frames` is populated, but rotation remains
  non-renderable because PCA frames are not trusted anatomical frames.
- `north_star_canonical_plan.json` — the **North Star**: a full generated
  straightening plan for the first tracked specimen
  (`spec-07b7031938c84b1a9c98517b8bc4cdd3`, the bundled OrthoCAD shells),
  produced by the real `landmark-derived` Generate Plan pipeline. Per-tooth crown
  **landmarks** drive real arch-form deviation targets, a space analysis budgets
  **IPR**, **attachments** are added on moved teeth, and approximate per-tooth
  **collision bounds** make the overlap check real. It is a mild/medium alignment
  projecting to ~4.2 months (9 stages at 14-day wear) with a `CONSISTENT` verdict.
  **Honesty note:** the specimen files are fused whole-arch shells with no
  segmentation, so the landmark coordinates are *approximate* scaffolding (not
  precise measurements); refining them to precise landmarks (or providing
  segmented meshes) raises fidelity further. Not a diagnosis, plan, or approval.

## Try them

```bash
pip install -e .
orthoplan plan-summary examples/basic_plan.json
orthoplan plan-summary examples/segmented_plan.json
orthoplan plan-summary examples/north_star_canonical_plan.json
```

## Regenerate

After a model change, regenerate and commit the updated JSON (a test asserts the
checked-in files match the generator output):

```bash
python examples/generate_examples.py
python examples/generate_north_star.py
```
