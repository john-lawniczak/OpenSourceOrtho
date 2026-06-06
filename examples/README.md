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
  produced by the real Generate Plan pipeline. It is a mild/medium anterior
  alignment that projects to ~4.7 months (10 stages at 14-day wear) with a
  `CONSISTENT` correctness verdict. **Honesty note:** the specimen files are
  fused whole-arch shells with no segmentation, so the per-tooth targets are
  *authored* estimates of a mild correction, not measurements of the patient's
  crowns; with segmented per-tooth meshes the same pipeline would derive the
  target from the visible geometry instead. Not a diagnosis, plan, or approval.

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
