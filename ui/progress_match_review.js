export function suggestedMatch(tooth, targets, current) {
  const proposed = Object.hasOwn(tooth, "independent_target_label") ? tooth.independent_target_label : tooth.target_tooth;
  const value = current ? current[tooth.tooth] : proposed;
  return targets.includes(value) ? value : "";
}

export function renderMatchReview(host,motion,current) {
  host.replaceChildren();
  const targets=motion.target_region_ids || motion.teeth.map(t=>t.tooth);
  for(const tooth of motion.teeth) {
    const label=document.createElement("label");label.textContent=`Baseline ${tooth.tooth} → later region`;
    const select=document.createElement("select");select.dataset.source=tooth.tooth;
    select.append(new Option("Hold / no match",""),...targets.map(id=>new Option(id,id)));
    select.value=suggestedMatch(tooth,targets,current);
    label.append(select);host.append(label);
  }
}
export function collectMatchReview(host) {
  const result={},targets=new Set();
  for(const select of host.querySelectorAll("select[data-source]")) {
    const value=select.value || null;
    if(value && targets.has(value))throw new Error("Assign each later region at most once.");
    if(value)targets.add(value);result[select.dataset.source]=value;
  }
  if(!Object.keys(result).length)throw new Error("Fit the scans before reviewing matches.");
  return result;
}
