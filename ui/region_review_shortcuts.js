// Shared bounds for buttons and keyboard; never consume text-entry keystrokes.
export function setupBrushShortcuts(onChange = () => {}) {
  const radius = document.getElementById("reviewRadius");
  function adjust(amount) {
    if (document.getElementById("reviewEditing").disabled) return;
    const next = Math.max(0.1, Math.min(10, (Number(radius.value) || 1) + amount));
    radius.value = next.toFixed(1);
    onChange();
    document.getElementById("reviewBrushStatus").textContent = `Brush radius ${next.toFixed(1)} scan units`;
  }
  radius.addEventListener("input", onChange);
  document.getElementById("reviewBrushSmaller").onclick = () => adjust(-0.1);
  document.getElementById("reviewBrushLarger").onclick = () => adjust(0.1);
  document.addEventListener("keydown", event => {
    if (event.ctrlKey || event.metaKey || event.altKey || event.target.closest("input, textarea, select, [contenteditable]")) return;
    if (event.key !== "[" && event.key !== "]") return;
    event.preventDefault(); adjust(event.key === "[" ? -0.1 : 0.1);
  });
}
