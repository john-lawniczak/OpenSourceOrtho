// Keep the parent section, camera and unfinished comparison alive while navigating.
let dialog, frame, returnFocus;
function close() { dialog.close(); returnFocus?.focus({ preventScroll: true }); }
document.addEventListener("click", event => {
  const link = event.target.closest?.("#openScanPair");
  if (!link || event.ctrlKey || event.metaKey || event.shiftKey || event.button) return;
  event.preventDefault(); returnFocus = link;
  if (!dialog) {
    dialog = document.createElement("dialog"); dialog.className = "precision-dialog";
    dialog.setAttribute("aria-label", "Compare two scans");
    const header = document.createElement("header"), back = document.createElement("button");
    back.type = "button"; back.id = "scanPairBack"; back.textContent = "← Back to scan history"; back.onclick = close;
    const title = document.createElement("strong"); title.textContent = "Compare two scans";
    header.append(back, title);
    frame = document.createElement("iframe"); frame.title = "Compare two scans";
    frame.src = "./progress.html?embedded=1";
    dialog.append(header, frame); document.body.append(dialog);
    dialog.addEventListener("cancel", event => { event.preventDefault(); close(); });
    window.addEventListener("message", event => {
      if (event.origin === location.origin && event.source === frame.contentWindow && event.data?.type === "scan-pair-return") close();
    });
  }
  dialog.showModal(); dialog.querySelector("button").focus();
});
