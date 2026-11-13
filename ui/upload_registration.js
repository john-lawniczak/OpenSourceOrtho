import { inferArchFromName } from "./core.js";

const requests = new WeakMap();
// Completion belongs to both this upload batch and this workspace. A newer
// registration also supersedes an older request for the same file array.
export async function registerUploadedScans(state, files, upload, storageWarning = "") {
  const request = Symbol("registration"), selectedArch = state.scanArch;
  requests.set(state, request);
  const current = () => requests.get(state) === request && state.files === files && !state.sample.active;
  const registered = [], errors = [];
  for (const file of files) {
    if (!current()) return false;
    const arch = selectedArch || inferArchFromName(file.name) || "";
    try {
      const result = await upload(file, { arch });
      if (result.ok === false) errors.push(`${file.name}: ${(result.errors || ["upload failed"]).join("; ")}`);
      else registered.push({ name: file.name, url: result.url, arch: arch || null, asset: result.asset });
    } catch (error) { errors.push(`${file.name}: ${error.message}`); }
  }
  if (!current()) return false;
  state.scanSources = registered;
  if (registered.length) {
    const detail = errors.length ? ` ${errors.length} upload(s) could not be registered.` : "";
    state.uploadStorageStatus = `Registered ${registered.length} scan file(s) with the local engine for segmentation and case metadata.${detail}`;
  } else if (errors.length) {
    state.uploadStorageStatus = `Loaded in this browser, but the local engine could not register the scan bytes: ${errors.join("; ")}`;
  }
  if (storageWarning) state.uploadStorageStatus += ` ${storageWarning}`;
  return true;
}
