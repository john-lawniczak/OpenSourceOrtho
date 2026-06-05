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

## Try them

```bash
pip install -e .
orthoplan plan-summary examples/basic_plan.json
orthoplan plan-summary examples/segmented_plan.json
```

## Regenerate

After a model change, regenerate and commit the updated JSON (a test asserts the
checked-in files match the generator output):

```bash
python examples/generate_examples.py
```
