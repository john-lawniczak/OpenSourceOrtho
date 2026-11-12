// Registration proposals retain their measured quality and matrix; review is explicit.
export function bindCbctRegistration(state, render) {
  const input=document.getElementById("cbctRegistrationFile");
  input.addEventListener("change",async()=>{
    const workflow=state.cbctWorkflow,file=input.files[0];input.value="";
    workflow.registrationReview=null;workflow.registrationAccepted=false;
    try {
      if(!file)return;
      if(file.size>1024*1024)throw new Error("Registration JSON exceeds size limit.");
      const record=JSON.parse(await file.text()),r=record.registration;
      if(!r?.matrix||!r.quality||!record.source_scan_sha256||!record.volume_source_digest)throw new Error("Choose the source-bound landmark registration report.");
      workflow.registrationReview=record;workflow.rmseMm=r.quality.rmse_mm;workflow.fitness=r.quality.fitness;
      workflow.status=`Loaded ${r.id}; held-out RMSE ${r.quality.rmse_mm ?? "unavailable"} mm. Inspect the transform and landmark report, then explicitly accept. Imported metrics and matrix take precedence over manual fields.`;
    }catch(error){workflow.status=error.message;}
    finally{render();}
  });
}
