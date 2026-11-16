import { profileFetch } from "./profile_context.js";
import { el, state } from "./state.js";
let lastKey = "", busy = false, pendingReview = null, reviewError = "", errorKey = "";
export const toothReviewPending = () => busy;
export const toothReviewError = () => errorKey === current().key ? reviewError : "";
function current() {
  const tooth = state.manualEdit.selectedTooth;
  const annotation = state.segmentation.annotations?.find(a => a.tooth_bindings?.[tooth]);
  return {tooth, annotation, key: annotation ? `${annotation.source_sha256}:${annotation.tooth_bindings[tooth]}` : ""};
}
export function renderToothReview() {
  const {tooth, annotation, key} = current(), review = annotation?.tooth_reviews?.[tooth];
  el("toothReviewDetails").hidden = !state.sample.active || !annotation;
  if (key !== lastKey) {
    lastKey = key; reviewError = "";
    el("toothReviewNotes").value = review?.notes || "";
    el("toothReviewer").value = review?.reviewer || "";
    el("toothReviewUncertain").checked = review?.status === "uncertain";
    el("toothReviewStatus").textContent = review ? `Contributor review saved ${review.created_at.slice(0,19)}.` : "No saved review for this region version.";
  }
  el("saveToothReview").disabled = busy || !annotation || Boolean(state.goalPreview) || state.goalBusy;
  for (const id of ["toothReviewer","toothReviewNotes","toothReviewUncertain"]) el(id).disabled = busy;
  el("reviewSelectedRegion").disabled ||= busy;
  if (busy && pendingReview?.key === key) el("reviewSelectedRegion").checked = pendingReview.checked;
}
export function installToothReview(renderAll) {
  async function save(checked) {
    if (busy || !state.sample.active || state.goalPreview || state.goalBusy) return;
    const {tooth, annotation, key} = current(); if (!annotation) return;
    const segmentation = state.segmentation;
    busy = true; reviewError = ""; pendingReview = {key,checked}; renderAll();
    try {
      const response = await profileFetch("/api/tooth-review", {method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({
        tooth, arch:annotation.arch, visit:state.sample.visit, source_sha256:annotation.source_sha256,
        mask_sha256:annotation.tooth_bindings[tooth], status:el("toothReviewUncertain").checked ? "uncertain" : checked ? "checked" : "unchecked",
        reviewer:el("toothReviewer").value, notes:el("toothReviewNotes").value,
      })});
      const result = await response.json();
      if (!response.ok || !result.ok) throw new Error(result.errors?.join("; ") || "Review could not be saved.");
      if (state.segmentation !== segmentation || !segmentation.annotations?.includes(annotation)) return;
      annotation.tooth_reviews ||= {}; annotation.tooth_reviews[tooth] = result.review;
      const link = segmentation.applied?.tooth_meshes.find(item => item.tooth.value === tooth);
      if (link) link.reviewed = result.review.status === "checked";
      state.availability = {...state.availability, segmented_teeth:segmentation.applied.tooth_meshes.every(item=>item.reviewed)};
      if (current().key === key) { lastKey = ""; renderToothReview(); }
    } catch(error) { errorKey = key; reviewError = `Review not saved: ${error.message}`; if (current().key === key) el("toothReviewStatus").textContent = reviewError; }
    finally { busy = false; pendingReview = null; renderAll(); }
  }
  el("reviewSelectedRegion").addEventListener("input", event => save(event.target.checked));
  el("saveToothReview").onclick = () => save(el("reviewSelectedRegion").checked);
}
