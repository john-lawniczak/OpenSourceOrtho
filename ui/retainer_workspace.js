// An isolated preparation flow; the parent sample/plan remains mounted on return.
let dialog,frame,returnFocus;
function close() { dialog.close();returnFocus?.focus({preventScroll:true}); }
document.addEventListener("click",event=>{
  const link=event.target.closest?.("#createRetainer");
  if(!link||event.ctrlKey||event.metaKey||event.shiftKey||event.button) return;
  event.preventDefault();returnFocus=link;
  if(!dialog) {
    dialog=document.createElement("dialog");dialog.className="precision-dialog";dialog.setAttribute("aria-label","Create Retainer");
    const header=document.createElement("header"),back=document.createElement("button"),title=document.createElement("strong");
    back.type="button";back.id="retainerWorkspaceBack";back.textContent="← Back to your workspace";back.onclick=close;
    title.textContent="Create Retainer · Reference preparation";header.append(back,title);
    frame=document.createElement("iframe");frame.title="Retainer reference preparation";frame.src="./retainer.html?embedded=1";
    dialog.append(header,frame);document.body.append(dialog);
    dialog.addEventListener("cancel",event=>{event.preventDefault();close();});
    window.addEventListener("message",event=>{if(event.origin===location.origin&&event.source===frame.contentWindow&&event.data?.type==="retainer-return") close();});
  }
  dialog.showModal();dialog.querySelector("button").focus();
});
