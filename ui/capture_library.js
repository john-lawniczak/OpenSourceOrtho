// Captures belong to one endpoint visit and arch; selecting one never adds a week.
import { el, scanFile, orientation } from "./progress_inputs.js";
export function createCaptureLibrary({ changed, status, activeCorrection }) {
  let groups = [[],[]], active = [null,null], loading = false;
  const field = (name,i) => el(`${name}${i}`);
  function current(i) { return groups[i].find(c=>c.id===active[i] && c.scan.arch===el("caseArch").value); }
  function stash(i) {
    const capture = current(i); if (!capture) return;
    capture.scan.date = field("date",i).value; capture.scan.rotation = orientation(i);
    capture.acquired = field("acquired",i).value; capture.model = field("model",i).value;
    capture.damage = field("damage",i).value; capture.correction = activeCorrection(i);
  }
  function render(i) {
    const eligible = groups[i].filter(c=>c.scan.arch===el("caseArch").value);
    field("activeCapture",i).replaceChildren(new Option("Choose a capture", ""), ...eligible.map(c=>new Option(c.scan.filename,c.id)));
    field("activeCapture",i).value = current(i)?.id || "";
    const capture = current(i);
    field("imported",i).textContent = capture?.imported_at ? `Added locally ${capture.imported_at.slice(0,19)}` : "";
    field("acquired",i).value = capture?.acquired || ""; field("model",i).value = capture?.model || "";
    field("damage",i).value = capture?.damage || "";
    if (capture) { field("date",i).value = capture.scan.date || ""; field("orientation",i).value = JSON.stringify(capture.scan.rotation || [1,1,1]); }
  }
  for (let i=0;i<2;i++) {
    const box = document.createElement("details"); box.open = true;
    box.innerHTML = `<summary>Captures for this visit</summary><label>Active capture <select id="activeCapture${i}"><option value="">Choose a capture</option></select></label>
      <label>Capture date <input id="acquired${i}" type="date"></label><label>Model / cast ID <input id="model${i}" maxlength="120"></label>
      <p id="imported${i}"></p><label>Damage or capture notes <textarea id="damage${i}" maxlength="2000"></textarea></label>`;
    field("scan",i).closest("fieldset").append(box); field("scan",i).multiple = true;
    field("scan",i).onchange = async () => {
      if (loading) return;
      loading = true; const arch = el("caseArch").value;
      try {
        stash(i);
        const files = [...field("scan",i).files];
        if (groups[i].length + files.length > 8) throw new Error("Keep at most eight captures per visit.");
        const bytes = groups.flat().reduce((n,c)=>n+c.scan.bytes.byteLength,0) + files.reduce((n,f)=>n+f.size,0);
        if (bytes > 180*1024*1024) throw new Error("This local case is limited to 180 MB of capture data.");
        const scans = await Promise.all(files.map(file=>scanFile(file,i)));
        for (const scan of scans) if (!groups[i].some(c=>c.id===`${arch}:${scan.sha256}`)) groups[i].push({
          id:`${arch}:${scan.sha256}`, scan:{...scan, arch, date:field("date",i).value, rotation:orientation(i)}, acquired:"", model:"", damage:"", imported_at:new Date().toISOString(), correction:null});
        if (!current(i) && scans.length === 1) active[i] = `${arch}:${scans[0].sha256}`;
        render(i); changed(i,current(i));
        status(`${groups[i].length} captures retained for this visit. Choose the active capture for fitting.`);
      } catch(error) { status(error.message); }
      finally { loading = false; field("scan",i).value = ""; }
    };
    for (const name of ["acquired","model","damage","date","orientation"]) field(name,i).addEventListener("input",()=>stash(i));
    field("activeCapture",i).onchange = () => { stash(i); active[i] = field("activeCapture",i).value || null; render(i); changed(i,current(i)); };
  }
  return {
    busy:()=>loading,
    snapshot() { [0,1].forEach(stash); return {groups, active}; },
    restore(record) {
      groups = record.captures?.groups || record.pair.map((scan,i)=>[{id:`${scan.arch}:${scan.sha256}`,scan,acquired:"",model:"",damage:"",correction:record.corrections[i]}]);
      active = record.captures?.active || groups.map(g=>g[0]?.id || null);
      [0,1].forEach(render);
    },
    archChanged() { [0,1].forEach(i=>{ render(i); changed(i,current(i)); }); },
    scans() {
      if (loading) throw new Error("Wait for capture import to finish.");
      [0,1].forEach(stash);
      return [0,1].map(i=>{const capture=current(i); if(!capture)throw new Error("Choose an active capture for each visit.");return capture.scan;});
    },
  };
}
