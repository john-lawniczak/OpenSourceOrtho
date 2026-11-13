import { el, state } from "./state.js";
import { saveUploadDates } from "./storage.js";
import { validCaptureDate, matchScanDates } from "./scan_dates.js";

let signature = "", renderedFiles;
export function renderScanDates() {
  const host = el("scanDates");
  if (!host) return;
  host.hidden = state.sample.active || !state.files.length;
  if (host.hidden) return;
  const files = state.files;
  const entries = matchScanDates(files, state.scanDates);
  const key = JSON.stringify(entries);
  if (key === signature && files === renderedFiles) return;
  signature = key; renderedFiles = files; host.replaceChildren();
  const help = document.createElement("p");
  help.textContent = "Scan dates are optional. Upload time is recorded separately; a file's modified date is not its scan date. Saved in this browser with your uploads.";
  host.append(help);
  for (const [index, file] of state.files.entries()) {
    const entry = entries[index];
    const row = document.createElement("div"); row.className = "scan-date-row";
    const title = document.createElement("strong"); title.textContent = file.name;
    const uploaded = document.createElement("small");
    uploaded.textContent = entry?.uploaded_at ? `Uploaded ${new Date(entry.uploaded_at).toLocaleString()}` : "Upload date unknown (earlier saved file)";
    const label = document.createElement("label"); label.textContent = "Scan taken on (optional)";
    const input = document.createElement("input"); input.type = "date"; input.value = entry?.captured_on || "";
    input.setAttribute("aria-label", `Scan taken on for ${file.name}`);
    input.addEventListener("input", async event => {
      event.stopPropagation();
      if (!validCaptureDate(input.value) || state.files !== files || state.sample.active) return;
      state.scanDates = matchScanDates(files, state.scanDates);
      state.scanDates[index] = { name: file.name, size: file.size, lastModified: file.lastModified,
        uploaded_at: null, ...state.scanDates[index], captured_on: input.value || null };
      signature = JSON.stringify(matchScanDates(files, state.scanDates));
      try { await saveUploadDates(state.scanDates); status.textContent = "Date saved in this browser."; }
      catch { status.textContent = "Date kept for this session; browser storage is unavailable."; }
    });
    label.append(input); row.append(title, uploaded, label); host.append(row);
  }
  const status = document.createElement("p"); status.setAttribute("role", "status"); host.append(status);
}
