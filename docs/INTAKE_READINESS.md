# Intake and Workflow Readiness

The Review workspace's **What can I trust here?** strip includes an expandable
**Record and workflow readiness** report. It describes the last successfully
evaluated plan. Editing the plan replaces the report with an updating message;
a failed evaluation leaves readiness unavailable. Older requests cannot publish
results after a newer edit is queued.

The report is a record of engineering evidence for the clear-aligner planning
safety playground and research toolkit. It does not establish diagnosis,
clinical authorization, physical fit, material performance, or safe physical use.

## Four separate evidence layers

| Layer | What it reports | What it does not establish |
|---|---|---|
| Record evidence | Each scan's arch label, declared units, bounds, recorded mesh quality, segmentation review, bite declaration, CBCT attachments, registration gates, and anatomy review | Local bytes being available, correct scan orientation, anatomical completeness, or independently validated records |
| Plan consistency | Whether stages exist, scale limits checks, and deterministic warnings need review | Biological suitability or clearance |
| Artifact prerequisites | The existing export prerequisite result and its blockers | Completed artifact geometry QA; QA runs during package export |
| Physical validation | Always `not_assessed` | Fit, forces, materials, manufacturing validation, or authorization for physical use |

There is deliberately no overall ready/approved boolean. A single-arch case can
show the other arch as missing without disabling surface work. CBCT dependencies
are labeled optional root/bone context; missing CBCT does not block surface review.

## Record interpretation

- **Recorded** (`present`) means the indicated metadata or review state exists.
  Read the row's detail for its scope; it does not certify the underlying record.
- **Missing** means the corresponding record or link is absent. Availability
  checkboxes do not substitute for scan, segmentation, or CBCT records.
- **Needs review** identifies unverified/non-mm units, implausible arch bounds,
  unlabeled or conflicting arch records, recorded mesh defects, partial tooth
  review, a declared bite without persisted registration evidence, or a marginal
  registration gate.
- **Blocked** identifies a failed registration or anatomy without explicit review,
  in-field coverage, and an open gate for that object's own registration.
- **Not assessed** identifies evidence the plan does not persist. In particular,
  reviewed segmentation links do not currently persist proposal quality-gate
  evidence. They remain distinguishable from a measured segmentation benchmark.

Scan scale observations reuse the existing arch bounds check. The report adds no
new geometric or clinical thresholds. Roots, axes, and bone are counted separately;
recording one domain never fills in another. Even when every recorded object has
passed its applicable gates, the report does not assert complete tooth coverage.

Action links open the corresponding Technician panel and focus the relevant
control. Links describe the next available workflow action; they do not silently
apply corrections, accept anatomy, or alter record declarations. Several issues
may require more than one action.

## API contract

`POST /api/evaluate` includes an additive `intake_readiness` object, also included
in the UI's downloaded evaluation JSON. Existing evaluation and export fields
retain their behavior.

- `schema_version`: currently `1`.
- `records`: typed rows with stable `id`, `label`, `state`, `detail`, `scope`,
  optional `asset_id`, and an optional action identifier. UI routes are mapped on
  the client; the engine emits no DOM selectors or HTML.
- `plan_consistency`: `status`, `warning_count`, and explanatory `detail`.
  Status is `no_stages`, `limited`, `findings_to_review`, or `checks_completed`.
- `artifacts`: `status` (`blocked` or `prerequisites_met`), `blockers`, `detail`,
  and `geometry_qa` (`not_run` in evaluation).
- `physical_validation`: always `not_assessed`.
- `caveat`: the report's evidence and interpretation limits.

Contracts live in `orthoplan/model/readiness.py`; deterministic derivation lives
in `orthoplan/evaluation/readiness.py` and its surface/CBCT helper modules.
The report consumes the existing evaluation findings, export status, scale
observations, and registration gates. It does not call model providers.

## Validation and remaining work

Regression tests cover empty, two-arch, partial, unlabeled, conflicting,
wrong-scale, noisy, and incompletely reviewed records; per-object registration
binding; and separation of export prerequisites from QA and physical validation.
UI tests cover escaped text, action routes, pending/error states, and out-of-order
evaluation responses. A browser regression uploads a synthetic user scan through
the actual intake endpoint and follows the unit-resolution link. The Review grid
adapts to available workspace width, including when both sidebars are open.
Existing browser smoke tests explicitly select Technician mode and add staged
rows where needed, matching the guided-first, empty-plan startup behavior.

Remaining Phase 13 work includes local-file/hash verification, persisted bite and
segmentation quality evidence, orientation checks, capability-specific gates,
and a full own-record journey through segmentation, generation, and export.
This report is an initial shared contract, not completion of the entire phase.
