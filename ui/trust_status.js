import { escapeHtml } from "./core.js";

function item(label, value, target, tone = "unknown") {
  return { label, value, target, tone };
}

export function trustStatusItems(state) {
  const result = state.lastEval || {};
  const tier = result.review_tier || {};
  const print = result.print_export || {};
  const readiness = print.manufacturing_readiness || {};
  const hasScan = Boolean(state.files?.length || state.scanSources?.length);
  const appliedCount = state.segmentation?.applied?.tooth_meshes?.length || 0;
  const hasProposal = Boolean(state.segmentation?.proposal?.teeth?.length);
  const segmentationBusy = Boolean(state.segmentation?.busy);
  const rootAware = Boolean(tier.root_bone_aware);
  const hasRootContext = Boolean(
    state.availability?.roots || state.availability?.cbct || state.derivedAnatomy?.roots?.length,
  );

  let provenance = "No active plan";
  if (state.sample?.active) provenance = "Sample fixture";
  else if (state.generation?.result?.source) provenance = state.generation.result.source;
  else if (state.rows?.length) provenance = "Manual or imported";

  let printValue = "Not evaluated";
  let printTone = "unknown";
  if (readiness.verdict === "CONSISTENT" && print.ready) {
    printValue = "Inputs consistent";
    printTone = "known";
  } else if (readiness.verdict === "ISSUES") {
    printValue = "Issues to review";
    printTone = "attention";
  } else if (readiness.verdict === "NOT_APPLICABLE") {
    printValue = "Not assessable";
    printTone = "attention";
  } else if (result.print_export) {
    printValue = print.ready ? "Review QA" : "Inputs incomplete";
    printTone = "attention";
  }

  return [
    item("Review tier", tier.label || "Not evaluated", "reviewTierBanner", tier.label ? "known" : "unknown"),
    item("Units", state.scanUnits === "mm" ? "Confirmed mm" : "Unverified", "scanUnits", state.scanUnits === "mm" ? "known" : "attention"),
    item("Geometry", hasScan ? (state.useDemoMeshes ? "Bundled demo" : "Uploaded scan") : "No scan", "scanMetadata", hasScan ? "known" : "unknown"),
    item("Segmentation", appliedCount ? `Applied draft · ${appliedCount}` : (segmentationBusy ? "Processing locally…" : (hasProposal ? "Awaiting review" : "Not proposed")), "segmentList", appliedCount ? "known" : ((segmentationBusy || hasProposal) ? "attention" : "unknown")),
    item("Root / bone", rootAware ? "Review available" : (hasRootContext ? "Context only" : "Unavailable"), "anatomyPanel", rootAware ? "known" : "attention"),
    item("Plan provenance", provenance, "generationStatus", provenance === "No active plan" ? "unknown" : "known"),
    item("Print readiness", printValue, "movementReadinessChecklist", printTone),
  ];
}

export function trustStatusMarkup(items) {
  return `
    <div class="trust-strip-heading">
      <strong>What can I trust here?</strong>
      <span>Known inputs and unresolved limits for this preview.</span>
    </div>
    <div class="trust-strip-items">
      ${items.map((entry) => `
        <a class="trust-status-item" data-tone="${escapeHtml(entry.tone)}" href="#${escapeHtml(entry.target)}">
          <span>${escapeHtml(entry.label)}</span>
          <strong>${escapeHtml(entry.value)}</strong>
        </a>
      `).join("")}
    </div>`;
}

export function renderTrustStatus(host, state) {
  if (!host) return;
  host.innerHTML = trustStatusMarkup(trustStatusItems(state));
}
