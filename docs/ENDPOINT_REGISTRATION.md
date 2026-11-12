# Endpoint fitting and reference regions

The local research fitter proposes a rigid target-to-baseline registration. It
checks symmetric surface residuals and repeats fitting with alternate samples
and perturbed rotation initialization. The resulting sensitivity is an empirical
stability diagnostic, not a calibrated measurement-error bound.

Projected crown matches now require a bounded nearest-surface distance, normal
agreement (absolute dot product to tolerate reversed STL winding), and a bounded
forward/reverse round trip. Rejected faces remain unassigned. Each accepted
face has one owner, and target face identities are retained for independent
benchmark scoring. Weak or unavailable tooth fits remain visible as draft or held.

Callers can supply reference.source_faces and reference.target_faces to
build_arch_preview. Both selections must be valid and nondegenerate. This limits
global fitting to selected geometry; it does not establish anatomical stability.
Without selections, whole-arch fitting may absorb genuine global arch movement.

The local USER_ONE baseline CBCT inventory was verified at Desktop/IMGDATA:
824 primary slices, 900 × 900, 0.2 mm spacing, plus one secondary image. The
ignored local pointer was repaired. Raw DICOM is neither committed nor served.
A baseline volume alone does not provide reviewed tooth labels, a reviewed
STL-to-CBCT transform, or a no-motion repeat. Those remain missing inputs for a
real anatomical accuracy benchmark; no accuracy score is inferred from file
availability or low surface residuals.
