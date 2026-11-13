// The shared viewer owns one selection, whether picked by raycast or FDI button.
import { renderViewerToothNumbers } from "./viewer_tooth_numbers.js";
import { el, state } from "./state.js";
import { renderProfile } from "./teeth_profile.js";
import { toothName, universalToothNumber, toothFromNumber } from "./tooth_selection.js";
import { escapeHtml } from "./core.js";
import { scaleConfirmed } from "./manual_edit.js";
let renderPreview = () => {};

export function selectableTeeth() {
  return [...new Set((state.segmentation.applied?.tooth_meshes || []).map(link => String(link.tooth.value)))].sort();
}

export function toothEditBlocker() {
  const tooth = state.manualEdit.selectedTooth;
  if (!tooth) return "Select a crown or its number below the viewer.";
  if (!scaleConfirmed(state.scanUnits)) return "Confirm scan units as mm in Upload.";
  if (!selectableTeeth().includes(tooth)) return "Identify and review individual teeth before editing.";
  if (!state.segmentation.applied?.tooth_meshes.find(link => String(link.tooth.value) === tooth)?.reviewed) return "Inspect this painted region, then check its number and boundary below before proposing movement.";
  if (state.guided.excludedTeeth.includes(tooth)) return "Release this tooth's hold to edit it.";
  if (state.goalPreview) return "Apply or discard the current preview first.";
  if (state.goalBusy) return "Preparing the preview…";
  return "";
}

export function renderToothWorkspace() {
  renderProfile();
  const teeth = selectableTeeth();
  const selected = state.manualEdit.selectedTooth;
  renderViewerToothNumbers(teeth, selected, state.showToothLabels);
  const blocker = toothEditBlocker();
  const scanned = Boolean(state.files.length || state.scanSources.length);
  el("simpleUpload").classList.toggle("has-scans", scanned);
  el("guidedViewerHost").hidden = !scanned;
  el("guidedViewerDetailsHost").hidden = !scanned;
  el("toothWorkspace").hidden = !scanned;
  const reviewed = (state.segmentation.applied?.tooth_meshes || []).filter(link => link.reviewed).length;
  el("toothSelectionStatus").textContent = teeth.length ? `${teeth.length} painted regions · ${reviewed} checked for edits` : "Identify and review teeth in step 2 to enable editing";
  el("guidedTeeth").innerHTML = [["1", "Upper right"], ["2", "Upper left"], ["4", "Lower right"], ["3", "Lower left"]].map(([quadrant, name]) => {
    const ids = teeth.filter(tooth => tooth.startsWith(quadrant));
    if (quadrant === "1" || quadrant === "4") ids.reverse();
    return `<fieldset><legend>${name}</legend>${ids.map(tooth => `<button type="button" data-select-tooth="${tooth}"
      title="${escapeHtml(toothName(tooth))}" aria-label="${tooth} · ${escapeHtml(toothName(tooth))}"
      aria-pressed="${selected === tooth}" class="tooth-pick ${state.guided.excludedTeeth.includes(tooth) ? "is-held" : ""}">${tooth}<small>US ${universalToothNumber(tooth)}</small></button>`).join("")}</fieldset>`;
  }).join("");
  el("guidedEditTitle").textContent = selected ? `FDI ${selected} · US ${universalToothNumber(selected)} · ${toothName(selected)}` : "Choose a tooth";
  el("guidedEditStatus").textContent = blocker || "Nudge by 0.2 mm in scan-local axes, or ask AI for a preview.";
  el("guidedEditReadout").textContent = "";
  el("reviewSelectedRegion").checked = Boolean(state.segmentation.applied?.tooth_meshes.find(link => link.tooth.value === selected)?.reviewed);
  el("reviewSelectedRegion").disabled = !selected || Boolean(state.goalPreview) || state.goalBusy;
  el("selectedRegionReview").hidden = !state.sample.active;
  for (const button of document.querySelectorAll("[data-manual-nudge]")) button.disabled = Boolean(blocker);
  el("guidedTargetReset").hidden = true; // Undo reverses an entire staged change without leaving later deltas behind.
  el("guidedRebuild").hidden = true; // Each preview is already staged by the engine.
  el("holdSelectedTooth").disabled = !selected || Boolean(state.goalPreview) || state.goalBusy;
  el("holdSelectedTooth").checked = state.guided.excludedTeeth.includes(selected);
  el("guidedEditUndo").disabled = !state.manualEdit.undoStack?.length || Boolean(state.goalPreview) || state.goalBusy;
  el("askSelectedTooth").disabled = !selected;
  el("guidedClearSelection").disabled = !selected;
  el("chatSelectedTooth").textContent = selected ? `tooth ${selected}` : "a selected tooth";
  el("chatEditMode").disabled = !selected;
  if (!selected) el("chatEditMode").checked = false;
  el("imagingScanList").textContent = (state.scanSources.map(source => source.name).filter(Boolean).join(" · ")
    || state.files.map(file => file.name).join(" · ")) || "Upload a scan in step 1 or open the sample.";
  renderPreview();
}

export function installToothWorkspace({ renderAll, renderGoalPreview, discardGoalPreview }) {
renderPreview = renderGoalPreview;
el("toothNumberForm").addEventListener("submit", event => {
  event.preventDefault();
  const tooth = toothFromNumber(el("toothNumberInput").value, el("toothNumberSystem").value);
  if (!tooth || !selectableTeeth().includes(tooth)) {
    el("toothNumberStatus").textContent = "No painted region is available for that number on this scan."; return;
  }
  state.manualEdit.selectedTooth = tooth; el("toothNumberStatus").textContent = `Selected FDI ${tooth} · US ${universalToothNumber(tooth)}`;
  renderAll();
});
el("reviewSelectedRegion").addEventListener("input", event => {
  if (!state.sample.active || state.goalPreview || state.goalBusy) return;
  const link = state.segmentation.applied?.tooth_meshes.find(item => item.tooth.value === state.manualEdit.selectedTooth);
  if (link) link.reviewed = event.target.checked;
  state.availability = { ...state.availability, segmented_teeth: state.segmentation.applied?.tooth_meshes.every(item => item.reviewed) || false };
  renderAll();
});
document.body.addEventListener("click", event => {
  const button = event.target.closest?.("button");
  if (button?.dataset.selectTooth) {
    state.manualEdit.selectedTooth = button.dataset.selectTooth;
    renderAll();
  }
  if (button?.id === "askSelectedTooth") {
    state.chat.collapsed = false; state.chat.caseSource = "workspace";
    el("chatEditMode").checked = true;
    el("chatInput").placeholder = `Describe a geometric change to tooth ${state.manualEdit.selectedTooth}…`;
    renderAll();
    el("chatInput").focus({ preventScroll: true });
  }
});
document.body.addEventListener("input", event => {
  if (event.target.id !== "holdSelectedTooth") return;
  if (state.goalPreview) discardGoalPreview();
  const selected = state.manualEdit.selectedTooth;
  const held = new Set(state.guided.excludedTeeth);
  if (event.target.checked) held.add(selected); else held.delete(selected);
  state.guided.excludedTeeth = [...held];
  renderAll();
});

}
