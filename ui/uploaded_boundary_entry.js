import { caseStore } from "./progress_case_store.js";
import { parseStlGeometry } from "./stl.js";
import { RegionEdits } from "./region_edits.js";
import { isBrowserParsableScan, looksLikePointCloud } from "./scan_formats.js";

let host, sources = [], signature;
export function renderBoundaryEntry(next) {
  if (!host) {
    host = document.createElement("section"); host.className = "boundary-entry";
    host.setAttribute("aria-label", "Tooth boundary editing");
    host.innerHTML = `<p><strong>Mark individual teeth</strong> — open the painting workspace for this scan.</p>
      <label>Scan<select id="boundaryScan"></select></label>
      <label>Arch<select id="boundaryArch"><option value="">Choose arch…</option><option value="upper">Upper</option><option value="lower">Lower</option></select></label>
      <button type="button" id="openBoundaryEditor">Edit tooth boundaries</button><p role="status" id="boundaryStatus"></p>`;
    document.getElementById("viewer3d").parentElement.after(host);
    host.querySelector("#boundaryScan").onchange = setArch;
    host.querySelector("#openBoundaryEditor").onclick = openEditor;
  }
  sources = next; host.hidden = !sources.length;
  const key = sources.map(s => `${s.name}:${s.arch}:${s.url}:${s.file?.lastModified}`).join("|");
  if (key === signature) return;
  signature = key;
  const select = host.querySelector("#boundaryScan"); select.replaceChildren();
  sources.forEach((source, index) => select.add(new Option(source.name, String(index))));
  setArch(); host.querySelector("#boundaryStatus").textContent = "";
}
function setArch() {
  const arch = sources[Number(host.querySelector("#boundaryScan").value)]?.arch;
  host.querySelector("#boundaryArch").value = ["lower", "mandibular"].includes(arch) ? "lower"
    : ["upper", "maxillary"].includes(arch) ? "upper" : "";
}
async function openEditor() {
  const button = host.querySelector("#openBoundaryEditor"), status = host.querySelector("#boundaryStatus");
  const source = sources[Number(host.querySelector("#boundaryScan").value)];
  const arch = host.querySelector("#boundaryArch").value;
  if (!source || !arch) { status.textContent = "Choose Upper or Lower before opening this scan."; return; }
  button.disabled = true; status.textContent = "Preparing the original surface…";
  try {
    let bytes;
    if (source.file && isBrowserParsableScan(source.name)) bytes = await source.file.arrayBuffer();
    else {
      const response = await fetch(source.url);
      if (!response.ok) throw new Error("Could not load this scan.");
      bytes = await response.arrayBuffer();
    }
    if (looksLikePointCloud(bytes)) throw new Error("Boundary painting needs a triangle surface; this file is a point cloud.");
    const geometry = parseStlGeometry(bytes), count = geometry.attributes.position.count / 3;
    geometry.dispose();
    if (!count) throw new Error("This scan has no triangles to paint.");
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    const sha256 = Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, "0")).join("");
    const name = `boundary-${crypto.randomUUID()}`;
    await caseStore("put", { name, returnToCase: false,
      scan: { bytes, arch, sha256, filename: source.name, rotation: [1, 1, 1], autoView: true },
      labels: new RegionEdits(new Uint8Array(count), arch).export(sha256) }, "edits");
    location.assign(`./region-review.html?edit=${encodeURIComponent(name)}`);
  } catch (error) { status.textContent = error.message; }
  finally { button.disabled = false; }
}
