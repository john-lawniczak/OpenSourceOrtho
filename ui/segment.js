// Advisory auto-segmentation client. Asks the local server (POST /api/segment)
// to propose per-tooth regions from the loaded whole-arch scan, then lets the
// user review/correct each tooth before EXPLICITLY applying them to the plan.
// Nothing is auto-accepted, and the proposal is model output: untrusted, drafty,
// and never a statement that a plan is safe or complete.

import { el, requestSegmentation, state } from "./state.js";

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
  for (const link of proposal.plan_fragment.tooth_meshes) {
    const edit = seg.edits[link.mesh_asset_id];
    if (!edit || !edit.included) continue;
    includedIds.add(link.mesh_asset_id);
    toothMeshes.push({ ...link, tooth: { system: "FDI", value: edit.tooth } });
  }
  const meshAssets = proposal.plan_fragment.mesh_assets.filter((asset) => includedIds.has(asset.id));
  seg.applied = toothMeshes.length ? { mesh_assets: meshAssets, tooth_meshes: toothMeshes } : null;
  seg.status = seg.applied
    ? `Applied ${toothMeshes.length} per-tooth mesh(es) to the plan. Still a draft — not a diagnosis.`
    : "No teeth selected to apply.";
}

export function setSegmentToothEdit(meshAssetId, value) {
  const edit = state.segmentation.edits[meshAssetId];
  if (edit) edit.tooth = value.trim();
}

export function setSegmentInclude(meshAssetId, included) {
  const edit = state.segmentation.edits[meshAssetId];
  if (edit) edit.included = included;
}
