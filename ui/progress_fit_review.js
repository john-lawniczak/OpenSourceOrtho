// Only bounded numeric fit evidence reaches the local helper; no raw scans or pixels.
export function bindFitReview(getMotion) {
  const button=document.getElementById("explainFit"),output=document.getElementById("fitExplanation");
  button.onclick=async()=>{
    const motion=getMotion();if(!motion){output.textContent="Complete a fit first.";return;}
    button.disabled=true;output.textContent="Reading fit evidence…";
    try {
      const teeth=motion.teeth.map(t=>({tooth:t.tooth,status:t.status,translation:t.translation,
        fit:t.fit?{p90_residual:t.fit.p90_residual,consistency:{sampling_shift:t.fit.consistency?.sampling_shift,round_trip_shift:t.fit.consistency?.round_trip_shift}}:null}));
      const response=await fetch("/api/motion-review",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({teeth,unit:motion.units_confirmation?.unit||"scan units"})});
      const report=await response.json();if(getMotion()!==motion)return;
      if(!response.ok||!report.ok)throw new Error(report.errors?.join("; ")||"Fit explanation unavailable");
      output.replaceChildren();
      for(const finding of report.findings){const p=document.createElement("p");p.textContent=`[ADVISORY — unverified] ${finding.title}: ${finding.message} (${finding.reference})`;output.append(p);}
      const note=document.createElement("small");note.textContent=`Local helper · ${report.evidence_scope}.`;output.append(note);
    }catch(error){if(getMotion()===motion)output.textContent=error.message;}
    finally{button.disabled=false;}
  };
}
