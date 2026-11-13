import { caseStore, saveEditRevision } from "./progress_case_store.js";

export function browserPaintingKey(scan) { return `boundary-${scan.sha256}-${scan.arch}`; }
export async function loadBrowserPainting(scan) {
  return await caseStore("get", browserPaintingKey(scan), "edits") || null;
}
export function browserSaveSummary(record) {
  // The shared saving controller treats saved_at as an opaque compare token.
  return record?.saved_at ? { ...record, saved_at: record.revision || record.saved_at,
    saved: true, corrections: record.labels, path: "Saved in this browser" } : null;
}
export async function saveBrowserPainting(scan, corrections, notes, baseSavedAt) {
  const record = { name: browserPaintingKey(scan), scan, labels: corrections, notes,
    returnToCase: false, saved_at: new Date().toISOString(), revision: crypto.randomUUID(),
    review_status: corrections.reviewed ? "reviewed" : "draft" };
  await saveEditRevision(record, baseSavedAt);
  return browserSaveSummary(record);
}
