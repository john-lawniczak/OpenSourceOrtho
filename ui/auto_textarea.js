export function autoGrowTextarea(field, minimum = 160) {
  function resize() {
    if (!field.getClientRects().length) return;
    field.style.height = "auto";
    field.style.height = `${Math.max(minimum, field.scrollHeight + 2)}px`;
  }
  field.addEventListener("input", resize);
  field.closest("details")?.addEventListener("toggle", resize);
  let width = 0;
  const observer = new ResizeObserver(entries => {
    const next = entries[0].contentRect.width;
    if (next !== width) { width = next; resize(); }
  });
  observer.observe(field);
  resize();
  return resize;
}
