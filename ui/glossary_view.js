import { glossaryTerms } from "./glossary.js";

const categories = {
  "Teeth & anatomy": ["Arch", "Canine", "FDI notation", "Incisor", "Molar", "Occlusion", "Premolar", "Quadrant"],
  "Bite & spacing": ["Class I bite", "Class II bite", "Class III bite", "Crowding", "Malocclusion", "Spacing"],
  "Movement & stages": ["Attachment", "Cumulative pose", "Extrusion", "Fixed tooth", "Intrusion", "IPR", "Movement cap", "Rotation", "Stage", "Tip", "Torque", "Translation", "Wear interval"],
};
let activeCategory = "All";
let search = "";

export function filterGlossary(query) {
  search = query.trim().toLowerCase();
  let visible = 0;
  for (const entry of document.querySelectorAll("#glossaryTerms > div")) {
    const match = (activeCategory === "All" || entry.dataset.category === activeCategory)
      && (!search || entry.textContent.toLowerCase().includes(search));
    entry.hidden = !match;
    if (match) visible++;
  }
  document.getElementById("glossaryEmpty").hidden = visible !== 0;
}

export function renderGlossaryTerms() {
  const list = document.getElementById("glossaryTerms");
  if (!list || list.dataset.rendered) return;
  for (const name of ["All", ...Object.keys(categories), "Scans & data"]) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = name;
    button.setAttribute("aria-pressed", String(name === activeCategory));
    button.addEventListener("click", () => {
      activeCategory = name;
      for (const item of button.parentElement.children) item.setAttribute("aria-pressed", String(item === button));
      filterGlossary(search);
    });
    document.getElementById("glossaryCategories").append(button);
  }
  for (const item of glossaryTerms) {
    const wrapper = document.createElement("div");
    const category = Object.keys(categories).find(name => categories[name].includes(item.term)) || "Scans & data";
    wrapper.dataset.category = category;
    const term = document.createElement("dt");
    const label = document.createElement("small");
    const definition = document.createElement("dd");
    label.textContent = category;
    term.append(label, document.createTextNode(item.term));
    definition.textContent = item.definition;
    wrapper.append(term, definition);
    list.append(wrapper);
  }
  list.dataset.rendered = "1";
}
