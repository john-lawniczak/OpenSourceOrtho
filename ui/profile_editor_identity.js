import { activeProfileId } from "./profile_context.js";
import { listProfiles } from "./profile_store.js";

const label = document.createElement("p");
label.className = "hint"; label.id = "editorProfileIdentity";
document.querySelector("main").prepend(label);
listProfiles().then(profiles => {
  const profile = profiles.find(item => item.id === activeProfileId);
  label.textContent = `Profile: ${profile?.name || "Unavailable"} · saves belong to this local workspace`;
}).catch(() => { label.textContent = "Profile storage is unavailable."; });
