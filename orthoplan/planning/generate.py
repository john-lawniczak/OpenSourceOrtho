"""Deterministic staged-plan generation.

``generate_plan`` turns whatever target signal is available into a cap-respecting
staged plan, reusing the existing optimizer for the actual staging. It has NO LLM
calls (per the ``planning/`` ownership rule); the consent-gated model review lives
in the top-level ``orthoplan/generation.py`` gateway.

Target resolution ("generate from whatever exists"), in priority order:

1. ``authored`` - the plan already has nonzero per-tooth movement; re-stage it.
2. ``geometry-derived`` - segmented per-tooth crown meshes exist; derive an
   arch-form straightening target from their visible positions (see
   ``planning/arch_form.py``).
3. ``educational-synthetic`` - only a raw scan; fall back to a clearly-labeled
   educational crowding template. This is NOT derived from the user's teeth, so
   the result carries a prominent warning and ``requires_acknowledgement``.

Nothing here diagnoses, infers unseen anatomy, or claims a plan is safe.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from orthoplan.model.assets import MeshAsset
from orthoplan.model.landmarks import ArchLandmarks
from orthoplan.model.plan import Stage, ToothDelta, TreatmentPlan
from orthoplan.planning.arch_form import archform_corrections
from orthoplan.planning.landmark_plan import build_landmark_inputs
from orthoplan.planning.optimizer import OptimizerIssue, _target_totals, optimize_staging

GenerationSource = Literal[
    "authored", "landmark-derived", "geometry-derived", "educational-synthetic", "none"
]

# Educational anterior crowding template (FDI -> initial scan-plane offset). The
# corrective target is the negative of these. Mirrors the UI demo offsets and is
# a fixed teaching dataset, never inferred from a real scan.
EDUCATIONAL_CROWDING_OFFSETS: dict[str, tuple[float, float]] = {
    "13": (0.35, -0.18), "12": (0.55, 0.28), "11": (-0.42, -0.32),
    "21": (0.44, 0.30), "22": (-0.52, -0.26), "23": (-0.32, 0.16),
    "43": (0.30, 0.14), "42": (0.48, -0.22), "41": (-0.36, 0.26),
    "31": (0.38, -0.28), "32": (-0.46, 0.24), "33": (-0.28, -0.12),
}

_GEOMETRY_WARNING = (
    "Targets are a geometric arch-form heuristic computed in unresolved scan-local "
    "axes from segmented crown bounds. It is not a clinical alignment goal, does not "
    "model roots or biological response, and is not an approval."
)
_SYNTHETIC_WARNING = (
    "No authored targets or segmented per-tooth meshes were available, so this uses a "
    "generic EDUCATIONAL crowding template. The movement is NOT derived from your scan "
    "and does not represent your actual teeth. Segment the arch to generate from your "
    "own geometry."
)
_CAVEAT = (
    "Generated staging splits a target into configured cap-sized increments. It is not "
    "a biological outcome model, does not decide whether treatment is safe, suitable, or "
    "complete, and does not replace a licensed dental professional."
)


class GeneratedPlanResult(BaseModel):
    plan: TreatmentPlan
    source: GenerationSource
    requires_acknowledgement: bool = False
    target_tooth_count: int = 0
    aligned_tooth_count: int = 0
    blocked_teeth: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    issues: list[OptimizerIssue] = Field(default_factory=list)
    # The resolved target totals (pre-staging). Exposed so the orchestrator can
    # regression-check that the staged plan's cumulative movement reaches them.
    requested_targets: list[ToothDelta] = Field(default_factory=list)
    # Space analysis (landmark-derived only): arch-length crowding and the part
    # IPR cannot resolve.
    space_discrepancy_mm: float | None = None
    space_residual_mm: float | None = None
    caveat: str = _CAVEAT


def generate_plan(
    plan: TreatmentPlan,
    *,
    acknowledge_educational: bool = False,
    landmarks: ArchLandmarks | None = None,
) -> GeneratedPlanResult:
    """Produce a cap-respecting staged plan from the best available target."""

    seed, targets, source, warnings, requires_ack, discrepancy, residual = _seed_plan(
        plan, landmarks
    )
    if not targets:
        return GeneratedPlanResult(
            plan=plan,
            source="none",
            warnings=[
                "Nothing to generate: no authored movement, no landmarks, no segmented "
                "teeth, and the educational template produced no targets."
            ],
        )

    if not plan.scale_confirmed:
        warnings.append(
            "Scan units are unverified, so per-stage millimeter caps cannot be compared; "
            "confirm units to enable cap evaluation."
        )

    optimized = optimize_staging(seed)
    blocked = sorted({issue.tooth for issue in optimized.issues})
    target_values = {delta.tooth.value for delta in targets}
    aligned = sorted(target_values - set(blocked))

    return GeneratedPlanResult(
        plan=optimized.plan,
        source=source,
        requires_acknowledgement=requires_ack and not acknowledge_educational,
        target_tooth_count=len(target_values),
        aligned_tooth_count=len(aligned),
        blocked_teeth=blocked,
        warnings=warnings,
        issues=optimized.issues,
        requested_targets=targets,
        space_discrepancy_mm=discrepancy,
        space_residual_mm=residual,
    )


def _seed_plan(
    plan: TreatmentPlan, landmarks: ArchLandmarks | None
) -> tuple[TreatmentPlan, list[ToothDelta], GenerationSource, list[str], bool, float | None, float | None]:
    """Resolve targets and return an (enriched) seed plan with a single target stage.

    The landmark path additionally enriches the plan with IPR, attachments, and
    approximate collision bounds; other paths only set the target stage.
    """

    # Authored movement always wins (re-stage what the user already entered).
    authored = _authored_targets(plan)
    if authored:
        seed = plan.model_copy(update={"stages": [Stage(index=0, deltas=authored)]})
        return seed, authored, "authored", [], False, None, None

    if landmarks is not None:
        inputs = build_landmark_inputs(landmarks, plan.coordinate_frame.name)
        if inputs.targets:
            seed = plan.model_copy(update={
                "mesh_assets": [*plan.mesh_assets, *inputs.mesh_assets],
                "tooth_meshes": [*plan.tooth_meshes, *inputs.tooth_meshes],
                "interproximal_reductions": [*plan.interproximal_reductions, *inputs.iprs],
                "attachments": [*plan.attachments, *inputs.attachments],
                "stages": [Stage(index=0, deltas=inputs.targets)],
            })
            return (seed, inputs.targets, "landmark-derived", inputs.warnings, False,
                    inputs.discrepancy_mm, inputs.residual_mm)

    geometry = _geometry_targets(plan)
    if geometry:
        seed = plan.model_copy(update={"stages": [Stage(index=0, deltas=geometry)]})
        return seed, geometry, "geometry-derived", [_GEOMETRY_WARNING], False, None, None

    synthetic = _synthetic_targets(plan)
    if synthetic:
        seed = plan.model_copy(update={"stages": [Stage(index=0, deltas=synthetic)]})
        return seed, synthetic, "educational-synthetic", [_SYNTHETIC_WARNING], True, None, None

    return plan, [], "none", [], False, None, None


def _authored_targets(plan: TreatmentPlan) -> list[ToothDelta]:
    totals = _target_totals(plan)
    return [delta for delta in totals.values() if delta.moved_axes()]


def _geometry_targets(plan: TreatmentPlan) -> list[ToothDelta]:
    assets = _assets_by_id(plan)
    frame = plan.coordinate_frame.name
    # Group occlusal-plane centroids by arch so each arch gets its own curve.
    by_arch: dict[str, dict[str, tuple[float, float]]] = {}
    for link in plan.tooth_meshes:
        asset = assets.get(link.mesh_asset_id)
        if asset is None or asset.bounds is None:
            continue
        cx = (asset.bounds.min_xyz[0] + asset.bounds.max_xyz[0]) / 2
        cy = (asset.bounds.min_xyz[1] + asset.bounds.max_xyz[1]) / 2
        by_arch.setdefault(link.tooth.arch.value, {})[link.tooth.value] = (cx, cy)

    targets: list[ToothDelta] = []
    tooth_lookup = {link.tooth.value: link.tooth for link in plan.tooth_meshes}
    for centroids in by_arch.values():
        for tooth_value, (dx, dy) in archform_corrections(centroids).items():
            if dx == 0.0 and dy == 0.0:
                continue
            targets.append(
                ToothDelta(
                    tooth=tooth_lookup[tooth_value],
                    translate_x_mm=dx,
                    translate_y_mm=dy,
                    coordinate_frame=frame,
                    source="model",
                )
            )
    return targets


def _synthetic_targets(plan: TreatmentPlan) -> list[ToothDelta]:
    # The educational fallback is only offered once a scan is loaded; an empty
    # plan generates nothing rather than a template out of thin air.
    if not plan.scans:
        return []
    frame = plan.coordinate_frame.name
    targets: list[ToothDelta] = []
    for tooth_value, (ox, oy) in EDUCATIONAL_CROWDING_OFFSETS.items():
        targets.append(
            ToothDelta(
                tooth={"system": "FDI", "value": tooth_value},
                translate_x_mm=-ox,
                translate_y_mm=-oy,
                coordinate_frame=frame,
                source="synthetic",
            )
        )
    return targets


def _assets_by_id(plan: TreatmentPlan) -> dict[str, MeshAsset]:
    assets = {asset.id: asset for asset in plan.mesh_assets}
    assets.update({scan.asset.id: scan.asset for scan in plan.scans})
    return assets
