// Fragment links into optional controls reveal their enclosing disclosures.
// Run in capture phase, before any workflow navigation handler moves focus.
document.addEventListener("click", (event) => {
  const link = event.target.closest?.('a[href^="#"]');
  const id = link?.getAttribute("href")?.slice(1);
  const target = id && document.getElementById(id);
  if (!target) return;
  for (let parent = target.parentElement; parent; parent = parent.parentElement) {
    if (parent.tagName === "DETAILS") parent.open = true;
  }
}, true);
