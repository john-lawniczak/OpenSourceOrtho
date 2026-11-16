// Freeze the profile for this document. Other tabs keep their own workspace.
export const validProfileId = id => id === "default" || /^[a-f0-9]{8}-(?:[a-f0-9]{4}-){3}[a-f0-9]{12}$/.test(id || "");
function selectedProfile() {
  try {
    const id = sessionStorage.getItem("orthoplan-active-profile") || localStorage.getItem("orthoplan-last-profile") || "default";
    if (!validProfileId(id)) return "default";
    sessionStorage.setItem("orthoplan-active-profile", id);
    return id;
  } catch { return "default"; }
}
export const activeProfileId = selectedProfile();
export const profileKey = key => activeProfileId === "default" ? key : `${key}:profile:${activeProfileId}`;
export function selectProfile(id) {
  if (!validProfileId(id)) throw new Error("Invalid profile.");
  sessionStorage.setItem("orthoplan-active-profile", id);
  try { localStorage.setItem("orthoplan-last-profile", id); } catch { /* This tab still retains its selection. */ }
}
export const profileHeaders = () => ({ "X-Ortho-Profile": activeProfileId });
export const profileFetch = (input, options = {}) => fetch(input, { cache: "no-store", ...options, headers: { ...options.headers, ...profileHeaders() } });
// A back/forward-cache restore revives this document's profile; child editors must inherit it.
globalThis.addEventListener?.("pageshow", event => { if (event.persisted) selectProfile(activeProfileId); });
