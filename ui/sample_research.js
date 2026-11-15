import { profileFetch } from "./profile_context.js";
// Explicit local experiments; bundled observations and previous fits stay intact.
import { geometryJob } from "./geometry_jobs.js";
import { validateMotionPreview, loadMotionPreview } from "./scan_motion_data.js";
import { downloadJson } from "./progress_case_archive.js";
const selected = new Map();
async function get(path, options) {
  const response = await profileFetch(path, options), result = await response.json();
  if (!response.ok || !result.ok) throw new Error(result.errors?.join("; ") || "Could not load research records.");
  return result;
}
export async function loadResearchMotion(pair, options) {
  const id = selected.get(pair[0].arch);
  if (!id) return loadMotionPreview(pair, options);
  const result = await get(`/api/sample-refits/${id}`, options);
  if (result.stale) throw new Error("Selected fit is stale. Rebuild from current labels or choose the bundled fit.");
  return validateMotionPreview(result.record.preview, pair);
}
export function installSampleResearch(host, reload) {
  const section = document.createElement("details");
  section.innerHTML = `<summary>Saved-label experiments</summary><div class="comparison-motion-tools">
    <label>Arch <select data-research="arch"><option value="upper">Upper</option><option value="lower">Lower</option></select></label>
    <button type="button" data-research="refresh">Refresh saved fits</button>
    <label>Preview <select data-research="fit"><option value="">Bundled fit</option></select></label>
    <button type="button" data-research="build">Refit saved painting</button>
    <button type="button" data-research="benchmark">Compare automatic labels</button>
    <button type="button" data-research="download" disabled>Download report</button>
    <button type="button" data-research="cancel" disabled>Cancel</button>
    </div><p data-research="status" role="status">Local experiments use week 1 and week 7 saved painting.</p>`;
  host.append(section);
  const field = name => section.querySelector(`[data-research="${name}"]`);
  let inputs = null, report = null, pending = null;
  const summary = s => `${s.fitted}/${s.regions} fitted · ${s.uncertain} uncertain · ${s.unmatched} unmatched · mean p90 ${s.mean_p90_residual?.toFixed(3) ?? "unavailable"} scan units`;
  async function refresh() {
    inputs = await get(`/api/sample-refits/${field("arch").value}`);
    field("fit").replaceChildren(new Option("Bundled fit", ""), ...inputs.versions.map(v => new Option(`${v.created_at.slice(0,19)} · ${v.stale ? "stale · " : ""}${summary(v.summary)}`, v.id)));
    field("fit").value = selected.get(field("arch").value) || "";
    field("status").textContent = `${inputs.versions.length} saved fits. Painting: ${inputs.inputs.annotations.map(a=>`${a.visit}: ${a.origin}`).join("; ")}.`;
  }
  async function action(fn) { try { await fn(); } catch(error) { field("status").textContent = error.message; } }
  field("refresh").onclick = () => action(refresh);
  field("arch").onchange = () => action(refresh);
  field("fit").onchange = () => action(async () => {
    const arch = field("arch").value, id = field("fit").value;
    if (id) {
      const result = await get(`/api/sample-refits/${id}`);
      report = result.record; field("download").disabled = false;
      if (result.stale) { field("fit").value = selected.get(arch) || ""; throw new Error("This fit used older inputs. Its report is available; rebuild or select another preview."); }
      field("status").textContent = summary(report.summary);
    } else field("status").textContent = "Showing the bundled fit for this arch.";
    selected.set(arch, id); await reload();
  });
  for (const [button, operation] of [["build","sample-refit"],["benchmark","sample-benchmark"]]) {
    field(button).onclick = () => action(async () => {
      if (pending) return;
      await refresh();
      const arch = field("arch").value, controller = new AbortController(); pending = controller;
      for (const name of ["arch","fit","build","benchmark","refresh"]) field(name).disabled = true;
      field("cancel").disabled = false; field("status").textContent = "Processing saved painting…";
      try {
        const result = await geometryJob(operation, { arch, input_digest: inputs.input_digest }, {signal:controller.signal});
        if (!result.ok) throw new Error(result.errors?.join("; ") || "Experiment failed");
        report = result.record; field("download").disabled = false;
        await refresh();
        if (button === "build") {
          selected.set(arch, report.id); field("fit").value = report.id;
          field("status").textContent = `Saved fit: ${summary(report.summary)}. Bundled: ${summary(report.comparison.original)}. Residuals measure surface agreement, not motion accuracy.`;
          await reload();
        } else field("status").textContent = `Saved contributor-agreement report. ${report.reports.map(r=>`${r.visit}: ${r.status === "compared" ? `mean tooth IoU ${r.macro_iou?.toFixed(3) ?? "unavailable"}` : "no contributor labels"}`).join("; ")}. This is not independent accuracy.`;
      } finally {
        pending = null; field("cancel").disabled = true;
        for (const name of ["arch","fit","build","benchmark","refresh"]) field(name).disabled = false;
      }
    });
  }
  field("cancel").onclick = () => pending?.abort();
  field("download").onclick = () => report && downloadJson(report, `research-${report.id}.json`);
}
