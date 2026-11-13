import { listEditNotes } from "./progress_case_store.js";

const list = document.getElementById("paintingNotesList");
const status = document.getElementById("paintingNotesStatus");
let generation = 0;

function noteCard(entry, source) {
  const card = document.createElement("article"); card.className = "painting-note";
  const title = document.createElement("h3"); title.textContent = entry.title;
  const meta = document.createElement("p"); meta.className = "hint";
  const date = new Date(entry.saved_at);
  meta.textContent = `${source} · ${entry.review_status} · ${Number.isNaN(date.getTime()) ? "Save date unknown" : date.toLocaleString()}`;
  const note = document.createElement("pre"); note.textContent = entry.notes || "No notes saved for this painting.";
  const link = document.createElement("a"); link.className = "painting-workspace-button";
  link.href = entry.href; link.textContent = "Open painting & notes";
  card.append(title, meta, note, link);
  return card;
}

async function refresh() {
  const current = ++generation;
  status.textContent = "Loading saved painting notes…";
  const results = await Promise.allSettled([
    listEditNotes(),
    fetch("/api/painting-notes").then(response => {
      if (!response.ok) throw new Error("Could not read sample notes.");
      return response.json();
    }),
  ]);
  if (generation !== current) return;
  const cards = [], errors = [];
  results.forEach((result, index) => {
    const source = index ? "On this computer" : "In this browser";
    if (result.status === "rejected") { errors.push(`Could not load notes ${source.toLowerCase()}. Try Refresh.`); return; }
    const entries = index ? result.value.entries : result.value;
    if (!Array.isArray(entries)) { errors.push("Sample notes response was invalid. Try Refresh."); return; }
    if (index) errors.push(...(result.value.errors || []));
    cards.push(...entries.map(entry => noteCard(entry, source)));
  });
  list.replaceChildren(...cards);
  status.textContent = [cards.length ? `${cards.length} saved ${cards.length === 1 ? "painting" : "paintings"}.` : "No saved painting notes found.", ...errors].join(" ");
}

document.getElementById("refreshPaintingNotes").addEventListener("click", refresh);
document.addEventListener("click", event => {
  if (event.target.closest?.('[data-step-target="notes"]')) refresh();
});
document.addEventListener("precision-workspace-closed", () => {
  if (document.body.dataset.step === "notes") refresh();
});
