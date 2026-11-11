export function renderMatchReview(host,motion,current) {
  host.replaceChildren();
  const targets=motion.target_region_ids || motion.teeth.map(t=>t.tooth);
  for(const tooth of motion.teeth) {
    const label=document.createElement("label");label.textContent=`Baseline ${tooth.tooth} → later region`;
    const select=document.createElement("select");select.dataset.source=tooth.tooth;
    select.append(new Option("Hold / no match",""),...targets.map(id=>new Option(id,id)));
    select.value=current ? current[tooth.tooth] || "" : targets.includes(tooth.tooth)?tooth.tooth:"";
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
