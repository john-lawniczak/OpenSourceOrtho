import { el, state } from "./state.js";
import { parseToothMentions, parseToothSelection } from "./tooth_selection.js";

const drafts = new Map();
let mounted = false, shownContext = "", redraw = () => {};
const context = () => state.sample.active ? "sample:USER_ONE" : `personal:${el("planId").value || "draft-001"}`;
const storageKey = key => `orthoplan-focus-teeth-v1:${key}`;
function entry(key = context()) {
  if (!drafts.has(key)) {
    let value = { teeth: [], enabled: false, edited: false, notice: "" };
    try {
      const stored = JSON.parse(localStorage.getItem(storageKey(key)) || "null");
      if (stored && Array.isArray(stored.teeth)) value = { ...value, teeth: parseToothSelection(stored.teeth.join(",")).teeth, enabled: stored.enabled === true, edited: true };
    } catch { value.notice = "Focus preferences could not be restored from this browser."; }
    drafts.set(key, value);
  }
  return drafts.get(key);
}
function save(value, key = context()) {
  value.edited = true;
  try { localStorage.setItem(storageKey(key), JSON.stringify({ teeth: value.teeth, enabled: value.enabled })); value.notice = "Saved in this browser for this plan."; }
  catch { value.notice = "Focus preferences could not be saved. They will last for this page only."; }
}
export function addNoteFocusTeeth(text, key) {
  const value = entry(key);
  const added = parseToothMentions(text).filter(id => !value.teeth.includes(id));
  if (!added.length) return;
  value.teeth.push(...added); save(value, key);
  if (context() === key) {
    // Preserve any unfinished manual list edit while showing the new saved tags.
    if (shownContext === key) {
      const input = el("focusTeethInput"), existing = parseToothSelection(input.value).teeth;
      const newIds = added.filter(id => !existing.includes(id));
      if (newIds.length) input.value = [input.value.trim(), ...newIds].filter(Boolean).join(", ");
    }
    redraw();
  }
}
export function seedSampleFocus(teeth) {
  const value = entry("sample:USER_ONE");
  if (!value.edited && Array.isArray(teeth)) {
    value.teeth = parseToothSelection(teeth.join(",")).teeth;
    if (state.sample.active) { shownContext = ""; redraw(); }
  }
}
export function focusedTeeth() {
  const value = entry();
  const available = new Set((state.segmentation.applied?.tooth_meshes || []).map(link => String(link.tooth.value)));
  return value.enabled ? value.teeth.filter(id => available.has(id)) : [];
}
export function renderFocusTeeth(renderAll) {
  redraw = renderAll;
  if (!mounted) {
    el("focusTeethInput").addEventListener("input", event => { event.stopPropagation(); entry().edited = true; });
    el("focusTeethForm").addEventListener("submit", event => {
      event.preventDefault(); event.stopPropagation();
      const result = parseToothSelection(el("focusTeethInput").value), value = entry();
      if (result.invalid.length) { el("focusTeethStatus").textContent = `Use valid FDI numbers. Check: ${result.invalid.join(", ")}`; return; }
      value.teeth = result.teeth; save(value); renderAll();
    });
    el("focusTeethToggle").addEventListener("click", () => { const value = entry(); value.enabled = !value.enabled; save(value); renderAll(); });
    mounted = true;
  }
  const key = context(), value = entry();
  if (shownContext !== key) { el("focusTeethInput").value = value.teeth.join(", "); shownContext = key; }
  el("focusTeethToggle").setAttribute("aria-checked", String(value.enabled));
  el("focusTeethToggle").classList.toggle("is-active", value.enabled);
  el("focusTeethToggle").disabled = !value.teeth.length;
  el("focusTeethToggle").title = value.teeth.length ? `My Highlighted Teeth: ${value.teeth.join(", ")}` : "Add FDI tooth numbers in Your plan first";
  const available = new Set((state.segmentation.applied?.tooth_meshes || []).map(link => String(link.tooth.value)));
  const missing = value.teeth.filter(id => !available.has(id));
  el("focusTeethStatus").textContent = [value.notice, missing.length ? `No painted region yet for ${missing.join(", ")}.` : ""].filter(Boolean).join(" ");
}
