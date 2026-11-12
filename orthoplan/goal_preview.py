"""Bounded, reviewable crown-translation proposals for a selected scan tooth.

Providers interpret a requested geometric change; deterministic staging owns all
poses and checks. This gateway never commits a plan or invents tooth boundaries.
"""
from __future__ import annotations

import re
from math import hypot
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from orthoplan.ai_chat import ChatRequest
from orthoplan.ai_workspace import workspace_context
from orthoplan.ai_connectors import build_chat_provider
from orthoplan.evaluation.finding import Finding, FindingLintError, lint_finding
from orthoplan.evaluation.providers.base import ModelProvider, ModelRequest
from orthoplan.hashing import canonical_json, sha256_text
from orthoplan.model import Stage, ToothDelta, TreatmentPlan
from orthoplan.planning.optimizer import _target_totals, optimize_staging
from orthoplan.planning.timeline import project_timeline


class Translation(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    x_mm: float = Field(default=0, ge=-4, le=4)
    y_mm: float = Field(default=0, ge=-4, le=4)


class Goal(Translation):
    tooth: str = Field(pattern=r"^[1-4][1-8]$")
    explanation: str = Field(min_length=1, max_length=1200)


class PreviewRequest(ChatRequest):
    selected_tooth: str = Field(pattern=r"^[1-4][1-8]$")
    adjustment: Translation | None = None


SYSTEM = """Interpret only the user's explicit geometric change to the selected
crown. Return JSON only: {"tooth":"11","x_mm":0.2,"y_mm":0,"explanation":"..."}.
x_mm and y_mm are ADDITIONAL translation from the existing final target in
scan-local millimetres: right=+x, left=-x, forward=+y, back=-y. These are scan axes,
not patient anatomical directions. Only the selected tooth may change. Each
axis and resulting total must stay within +/-4 mm (an editor limit, not a
clinical threshold). Do not prescribe movement from scan appearance, diagnose,
recommend treatment, claim safety or approval, change z/rotation, or execute code.
If amount/direction is ambiguous or the request is clinical, return zero x/y and
ask for an explicit geometric change in explanation. Explain the proposal briefly.
"""


def _gate(plan: TreatmentPlan, tooth: str) -> None:
    if not plan.scans or any(scan.asset.units != "mm" for scan in plan.scans):
        raise ValueError("Confirm scan units as mm before editing a tooth.")
    if plan.coordinate_frame.name != "scan-local":
        raise ValueError("Tooth previews currently require scan-local axes.")
    asset_ids = {asset.id for asset in plan.mesh_assets if asset.units == "mm" and asset.face_count > 0}
    if not any(link.tooth.value == tooth and link.reviewed and link.mesh_asset_id in asset_ids for link in plan.tooth_meshes):
        raise ValueError("Review and apply this tooth's segmentation before editing.")
    if any(item.tooth.value == tooth for item in plan.fixed_teeth):
        raise ValueError("Release the selected tooth's hold before editing.")
    if any(item.tooth.value == tooth for item in plan.movement_exclusions):
        raise ValueError("This tooth has movement exclusions. Review its controls first.")


def _local_goal(request: PreviewRequest) -> Goal:
    # Deliberately narrow grammar; never guess movement from a treatment request.
    match = re.fullmatch(r"(?:move|shift|nudge)(?:\s+(?:it|tooth\s+\d{2}))?\s+"
                         r"(\d+(?:\.\d+)?)\s*mm\s+(right|left|forward|back)[.!]?",
                         request.message.strip(), re.I)
    if not match:
        raise ValueError('Specify a geometric change, e.g. "move 0.2 mm right", or choose an AI provider in Settings.')
    amount, direction = float(match[1]), match[2].lower()
    mentioned = re.search(r"tooth\s+(\d{2})", request.message, re.I)
    if mentioned and mentioned[1] != request.selected_tooth:
        raise ValueError("Select the requested tooth first.")
    value = -amount if direction in {"left", "back"} else amount
    return Goal(tooth=request.selected_tooth,
                x_mm=value if direction in {"left", "right"} else 0,
                y_mm=value if direction in {"forward", "back"} else 0,
                explanation=f"Preview an additional {amount:g} mm {direction} in scan-local axes.")


def _resolve_goal(request: PreviewRequest, plan: TreatmentPlan, provider: ModelProvider | None) -> Goal:
    if request.adjustment is not None:
        return Goal(tooth=request.selected_tooth, **request.adjustment.model_dump(),
                    explanation="Preview the requested nudge in scan-local axes.")
    if provider is None and request.provider == "local":
        return _local_goal(request)
    if not request.share_acknowledged:
        raise ValueError("Enable external AI access in Settings before sending a tooth goal.")
    used = provider or build_chat_provider(request.provider, model=request.model,
                                          api_key=request.api_key, endpoint=request.endpoint)
    totals = _target_totals(plan)
    current = totals.get(request.selected_tooth)
    # Send only the selected target, never mesh bytes or an unnecessary full case.
    context = {"selected_tooth": request.selected_tooth, "message": request.message,
               "current_target": current.model_dump(mode="json") if current else None,
               "workspace": workspace_context(plan)}
    response = used.complete(ModelRequest(system=SYSTEM, prompt=canonical_json(context), metadata={}))
    return Goal.model_validate_json(response.text)


def _candidate(plan: TreatmentPlan, goal: Goal, source: str) -> TreatmentPlan:
    totals = _target_totals(plan)
    current = totals.get(goal.tooth) or ToothDelta(tooth={"system": "FDI", "value": goal.tooth},
                                                   coordinate_frame=plan.coordinate_frame.name)
    x, y = current.translate_x_mm + goal.x_mm, current.translate_y_mm + goal.y_mm
    if abs(x) > 4 or abs(y) > 4:
        raise ValueError("The final target exceeds the editor's ±4 mm limit. Request a smaller change.")
    # Preserve authored paths, stage timing, controls and provenance. Only stage
    # the additional translation, then append it after the existing timeline.
    delta = ToothDelta(tooth=current.tooth, translate_x_mm=goal.x_mm,
                       translate_y_mm=goal.y_mm, coordinate_frame=plan.coordinate_frame.name,
                       mesh_asset_id=current.mesh_asset_id, source=source)
    caps = plan.settings.movement_caps.caps_for(goal.tooth)
    if hypot(goal.x_mm, goal.y_mm) > 512 * caps.linear_mm:
        raise ValueError("This preview would exceed 512 additional stages; increase the cap or reduce the change.")
    # The gate already rejects controls on this tooth. Other teeth's distant
    # control endpoints must not expand this single-tooth staging search.
    addition = plan.model_copy(update={"stages": [Stage(index=0, deltas=[delta])],
                                       "fixed_teeth": [], "movement_exclusions": []})
    result = optimize_staging(addition)
    if result.issues:
        raise ValueError("The proposal conflicts with movement controls; the current plan was kept.")
    offset = len(plan.stages)
    appended = [stage.model_copy(update={"index": offset + i}) for i, stage in enumerate(result.plan.stages)]
    return plan.model_copy(update={"stages": [*plan.stages, *appended]})


def preview_goal_payload(payload: dict[str, Any], *, provider: ModelProvider | None = None) -> dict[str, Any]:
    try:
        request = PreviewRequest.model_validate(payload)
        plan = TreatmentPlan.model_validate(request.plan)
        _gate(plan, request.selected_tooth)
        goal = _resolve_goal(request, plan, provider)
        if goal.tooth != request.selected_tooth:
            raise ValueError("The response changed a different tooth. Select that tooth and try again.")
        finding = lint_finding(Finding(severity="info", category="education", provenance="MODEL",
                                       title="Geometric preview", message=goal.explanation))
        if not goal.x_mm and not goal.y_mm:
            return {"ok": True, "clarification": finding.message, "finding": finding.model_dump(mode="json")}
        source = "manual" if request.adjustment is not None else "model"
        candidate = _candidate(plan, goal, source)
        return {"ok": True, "plan": candidate.model_dump(mode="json"),
                "baseline_hash": sha256_text(canonical_json(plan.model_dump(mode="json"))),
                "change": goal.model_dump(), "finding": finding.model_dump(mode="json"),
                "timeline": project_timeline(candidate).model_dump()}
    except FindingLintError:
        return {"ok": False, "errors": ["The model explanation failed the text check. No changes were made."]}
    except ValidationError:
        return {"ok": False, "errors": ["The request or model response did not match the bounded tooth-edit format."]}
    except ValueError as exc:
        return {"ok": False, "errors": [str(exc)]}
    except Exception:
        return {"ok": False, "errors": ["The tooth preview could not be generated. No changes were made."]}
