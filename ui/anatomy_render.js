import { escapeHtml } from "./core.js";
import { el, state } from "./state.js";

const GROUPS = ["roots", "tooth_axes", "alveolar_bone"];
const GROUP_LABELS = {
  roots: "Root geometry",
  tooth_axes: "Tooth axis",
  alveolar_bone: "Alveolar bone",
};

export function anatomyCounts(anatomy) {
  return Object.fromEntries(GROUPS.map((group) => [group, anatomy?.[group]?.length || 0]));
}

export function guidedAnatomyMarkup(anatomy) {
  const counts = anatomyCounts(anatomy);
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
  const trusted = GROUPS.reduce(
    (sum, group) => sum + (anatomy?.[group] || []).filter((item) => item.trusted).length,
    0,
  );
  return `
    <p class="review-tier-note"><strong>${trusted} of ${total}</strong> reviewed anatomy objects are trusted and in field.</p>
    <ul class="anatomy-summary-list">
      <li>${counts.roots} root geometries</li>
      <li>${counts.tooth_axes} tooth axes</li>
      <li>${counts.alveolar_bone} alveolar-bone record(s)</li>
    </ul>
    <button class="anatomy-detail-action" data-user-mode="advanced" type="button">Review anatomy in Technician mode</button>
  `;
}

export function renderAnatomyReview(anatomy) {
  const panel = el("anatomyPanel");
  const list = el("anatomyReviewList");
  if (!panel || !list) return;
  const counts = anatomyCounts(anatomy);
  const total = Object.values(counts).reduce((sum, count) => sum + count, 0);
  if (!anatomy || total === 0) {
    panel.hidden = true;
    list.innerHTML = "";
    return;
  }
  panel.hidden = false;
  if (state.userMode === "simple") {
    list.innerHTML = guidedAnatomyMarkup(anatomy);
    return;
  }
  const sections = GROUPS.map((group) =>
    (anatomy[group] || []).map((item, index) => anatomyRowMarkup(group, index, item)).join(""),
  ).join("");
  const trustNote = anatomy.has_trusted
    ? "At least one object is trusted (reviewed and in field)."
    : "No object is trusted yet - root/bone-aware checks stay unavailable (fail-closed).";
  list.innerHTML = `<p class="review-tier-note">${escapeHtml(trustNote)}</p>${sections}`;
}

function anatomyRowMarkup(group, index, item) {
  const label = GROUP_LABELS[group] || group;
  const tooth = item.tooth?.value ? ` ${item.tooth.value}` : "";
  const confidence = item.confidence != null ? ` · conf ${Number(item.confidence).toFixed(2)}` : "";
  const flags = [
    item.trusted ? "trusted" : "not trusted",
    item.out_of_field ? "out of field" : null,
  ].filter(Boolean).join(" · ");
  const button = (status, text) => `<button data-anatomy-review="${status}" data-anatomy-group="${group}" data-anatomy-index="${index}" type="button">${text}</button>`;
  return `
    <div class="segment-row anatomy-row" data-status="${escapeHtml(item.review_status)}">
      <span><strong>${escapeHtml(label)}${escapeHtml(tooth)}</strong> · ${escapeHtml(item.review_status)}${escapeHtml(confidence)}</span>
      <small>${escapeHtml(flags)}</small>
      <span class="anatomy-actions">${button("accepted", "Accept")}${button("corrected", "Correct")}${button("rejected", "Reject")}</span>
    </div>`;
}
