import { parseStlGeometry } from "./stl.js";
import { manifoldFacePairs, disconnectedPatches } from "./region_fragment_topology.js";

export function setupFragmentReview(getState, selectTooth) {
  const el = id => document.getElementById(id);
  let pairs = null, groups = [], revision = 0, busy = false;
  function clear(message) {
    revision++; busy = false; groups = [];
    el("reviewFindFragments").disabled = false;
    el("reviewFragmentChoice").replaceChildren();
    for (const id of ["reviewFragmentChoice", "reviewFragmentPrev", "reviewFragmentNext", "reviewShowFragments"]) el(id).disabled = true;
    el("reviewShowFragments").checked = false;
    el("reviewFragmentSummary").textContent = message;
    el("reviewFragmentStatus").textContent = "";
    getState().viewer?.showFragments([], false);
  }
  function focus(index) {
    if (!groups.length) return;
    index = (index + groups.length) % groups.length;
    const group = groups[index];
    el("reviewFragmentChoice").selectedIndex = index;
    el("reviewShowFragments").checked = true;
    selectTooth(group.label);
    getState().viewer.showFragments(groups, true);
    getState().viewer.focusFragment(group);
    el("reviewFragmentStatus").textContent = `Patch ${index + 1} of ${groups.length} · FDI ${group.label} · ${group.faces.length} ${group.faces.length === 1 ? "triangle" : "triangles"}`;
  }
  el("reviewFindFragments").onclick = async () => {
    if (busy || !getState().scan) return;
    busy = true; const current = ++revision;
    el("reviewFindFragments").disabled = true;
    el("reviewFragmentSummary").textContent = "Checking connected surfaces…";
    await new Promise(resolve => setTimeout(resolve, 30));
    if (current !== revision) return;
    try {
      const { scan, edits, viewer } = getState();
      if (!pairs) {
        const raw = parseStlGeometry(scan.bytes);
        try { pairs = manifoldFacePairs(raw.attributes.position.array); } finally { raw.dispose(); }
      }
      groups = disconnectedPatches(edits.labels, pairs);
      const rightQuadrant = scan.arch === "upper" ? 1 : 4;
      const right = groups.filter(g => Math.floor(g.label / 10) === rightQuadrant).reduce((n, g) => n + g.faces.length, 0);
      const total = groups.reduce((n, g) => n + g.faces.length, 0);
      el("reviewFragmentSummary").textContent = groups.length
        ? `Right: ${right} · Left: ${total - right} triangles · ${groups.length} patches`
        : "No disconnected labeled patches found. This does not verify tooth boundaries.";
      el("reviewFragmentChoice").replaceChildren(...groups.map((g, i) => new Option(`${i + 1}. FDI ${g.label} · ${g.faces.length} triangles`, String(i))));
      for (const id of ["reviewFragmentChoice", "reviewFragmentPrev", "reviewFragmentNext", "reviewShowFragments"]) el(id).disabled = !groups.length;
      el("reviewShowFragments").checked = Boolean(groups.length);
      viewer.showFragments(groups, Boolean(groups.length));
      if (groups.length) focus(0);
    } catch (error) { clear(`Could not inspect patches: ${error.message}`); }
    finally { busy = false; el("reviewFindFragments").disabled = false; }
  };
  el("reviewFragmentChoice").onchange = () => focus(el("reviewFragmentChoice").selectedIndex);
  el("reviewFragmentPrev").onclick = () => focus(el("reviewFragmentChoice").selectedIndex - 1);
  el("reviewFragmentNext").onclick = () => focus(el("reviewFragmentChoice").selectedIndex + 1);
  el("reviewShowFragments").onchange = () => getState().viewer?.showFragments(groups, el("reviewShowFragments").checked);
  return {
    reset() { pairs = null; clear("Find patches outside each label’s main connected region."); },
    invalidate() { clear("Labels changed. Find patches again to update the highlights."); },
  };
}
