// Advisory auto-segmentation client. Asks the local server (POST /api/segment)
// to propose per-tooth regions from the loaded whole-arch scan, then lets the
// user review/correct each tooth before EXPLICITLY applying them to the plan.
// Nothing is auto-accepted, and the proposal is model output: untrusted, drafty,
// and never a statement that a plan is safe or complete.

import { requestSegmentation, state } from "./state.js";

// Valid FDI two-digit notation: quadrant 1-8, position 1-8. Mirrors the engine's
// ToothId validator so a corrected number can never reach the plan and silently
// fail whole-plan evaluation with a cryptic rejection.
const FDI_RE = /^[1-8][1-8]$/;

export function isValidFdi(value) {
  return FDI_RE.test(String(value || "").trim());
}

export async function proposeSegmentation() {
  const seg = state.segmentation;
  if (seg.busy) return;
  const scans = state.scanSources.map((source) => ({
    reference: source.url || source.name,
    arch: source.arch,
  }));
  if (!scans.length) {
    seg.status =
      "Load the Sample Test Case (or example scans) first. Uploaded files stay in " +
      "your browser, so the local server cannot segment them yet.";
    return;
  }
  seg.busy = true;
  seg.status = "Proposing per-tooth segmentation on this machine...";
  try {
    const result = await requestSegmentation({ scans });
    if (result.ok === false) {
      seg.proposal = null;
      seg.status = (result.errors || ["segmentation failed"]).join("; ");
    } else {
      seg.proposal = result;
      seg.edits = {};
      for (const tooth of result.teeth) {
        seg.edits[tooth.mesh_asset_id] = { tooth: tooth.tooth, included: true };
      }
      seg.status =
        `Draft ready · ${result.teeth.length} teeth · overall confidence ` +
        `${result.overall_confidence}. Review and correct, then apply.`;
    }
  } catch (error) {
    seg.proposal = null;
    seg.status = error.message;
  } finally {
    seg.busy = false;
  }
}

// Build the accepted (and possibly corrected) plan fragment from the per-tooth
// edits. This is the only place a proposal turns into plan data.
export function applySegmentation() {
  const seg = state.segmentation;
  const proposal = seg.proposal;
  if (!proposal) return;
  const includedIds = new Set();
  const toothMeshes = [];
  let invalid = 0;
  for (const link of proposal.plan_fragment.tooth_meshes) {
    const edit = seg.edits[link.mesh_asset_id];
    if (!edit || !edit.included) continue;
    const value = String(edit.tooth || "").trim();
    if (!isValidFdi(value)) {
      invalid += 1;
      continue;
    }
    includedIds.add(link.mesh_asset_id);
    toothMeshes.push({ ...link, tooth: { system: "FDI", value } });
  }
  const meshAssets = proposal.plan_fragment.mesh_assets.filter((asset) => includedIds.has(asset.id));
  seg.applied = toothMeshes.length ? { mesh_assets: meshAssets, tooth_meshes: toothMeshes } : null;
  const skipped = invalid ? ` Skipped ${invalid} tooth(s) with an invalid FDI number (use two digits, each 1-8).` : "";
  if (seg.applied) {
    seg.status = `Applied ${toothMeshes.length} per-tooth mesh(es) to the plan. Still a draft — not a diagnosis.${skipped}`;
  } else {
    seg.status = invalid ? `No valid teeth to apply.${skipped}` : "No teeth selected to apply.";
  }
}

export function setSegmentToothEdit(meshAssetId, value) {
  const edit = state.segmentation.edits[meshAssetId];
  if (edit) edit.tooth = value.trim();
}

export function setSegmentInclude(meshAssetId, included) {
  const edit = state.segmentation.edits[meshAssetId];
  if (edit) edit.included = included;
}
