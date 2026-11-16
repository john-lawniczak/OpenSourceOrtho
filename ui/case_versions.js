import { profileHeaders } from "./profile_context.js";

export async function savePlanVersion(payload) {
  const response = await fetch("/api/plan/version", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...profileHeaders() },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => ({}));
    throw new Error((detail.errors || ["save failed"]).join("; "));
  }
  return response.json();
}
export async function listCaseVersions(caseId) {
  const response = await fetch(`/api/cases/${encodeURIComponent(caseId)}`, { headers: profileHeaders() });
  if (!response.ok) return { ok: false, versions: [] };
  return response.json();
}
