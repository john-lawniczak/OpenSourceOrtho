import { el, state } from "./state.js";
import { confidenceTier, countNoteMarkup, escapeHtml } from "./core.js";
import { parseMissingTeeth } from "./segment.js";

export function segmentRowMarkup(tooth, edit) {
  const effectiveEdit = edit || { tooth: tooth.tooth, included: true };
  const pct = Math.round((tooth.confidence || 0) * 100);
  const tier = confidenceTier(pct);
  const review = tier === "low" ? "Review" : "";
  return `
    <div class="segment-row">
      <input type="checkbox" data-segment-include="${escapeHtml(tooth.mesh_asset_id)}" ${effectiveEdit.included ? "checked" : ""} aria-label="Include this tooth" />
      <input class="segment-tooth" data-segment-tooth="${escapeHtml(tooth.mesh_asset_id)}" value="${escapeHtml(effectiveEdit.tooth)}" maxlength="2" aria-label="FDI tooth number" />
      <span class="segment-arch">${escapeHtml(tooth.arch)}</span>
      <span class="segment-conf" data-tier="${tier}"><span class="segment-conf-bar" style="width:${pct}%"></span></span>
      <span class="segment-conf-num" data-tier="${tier}">${pct}%${review ? ` · ${review}` : ""}</span>
    </div>`;
}

export function renderSegmentation() {
  const seg = state.segmentation;
  const status = el("segmentStatus");
  if (!status) return;
  status.textContent = seg.busy ? "Working..." : "";
  el("proposeSegment").disabled = seg.busy;

  const proposal = seg.proposal;
  el("segmentFindings").innerHTML = proposal?.advisory_findings?.length
    ? proposal.advisory_findings
        .map((finding) => `<li>${escapeHtml(finding.title)}: ${escapeHtml(finding.message)}</li>`)
        .join("")
    : "";

  const reanchor = el("reanchorSegment");
  const list = el("segmentList");
  if (!proposal?.teeth?.length) {
    list.innerHTML = seg.status ? `<p class="viewer-caveat">${escapeHtml(seg.status)}</p>` : "";
    el("applySegment").hidden = true;
    el("segmentApplied").textContent = "";
    if (reanchor) reanchor.hidden = true;
    return;
  }
  if (reanchor) {
    reanchor.hidden = false;
    reanchor.disabled = seg.busy;
  }
  const markedGapCount = parseMissingTeeth(seg.missingTeeth).length;
  list.innerHTML =
    `<p class="viewer-caveat">${escapeHtml(seg.status)}</p>` +
    countNoteMarkup(proposal.teeth, markedGapCount) +
    proposal.teeth
      .map((tooth) => segmentRowMarkup(tooth, seg.edits[tooth.mesh_asset_id]))
      .join("");
  el("applySegment").hidden = false;
  el("segmentApplied").textContent = seg.applied
    ? `Applied: ${seg.applied.tooth_meshes.length} tooth mesh(es) merged into the plan (draft).`
    : "Not applied yet.";
}
