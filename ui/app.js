import { el, maxStage, state } from "./state.js";
import { renderAll, renderAvailability, setDimension } from "./render.js";

document.querySelectorAll(".step").forEach((button) => {
  button.addEventListener("click", () => {
    state.activeStep = button.dataset.step;
    renderAll();
  });
});

document.querySelectorAll(".mode").forEach((button) => {
  button.addEventListener("click", () => {
    state.view = button.dataset.view;
    document.querySelectorAll(".mode").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    renderAll();
  });
});

document.querySelectorAll(".dim").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll(".dim").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    setDimension(button.dataset.dim);
  });
});

el("stlFile").addEventListener("change", (event) => {
  state.file = event.target.files[0] || null;
  el("uploadLabel").textContent = state.file ? state.file.name : "Choose STL file";
  renderAll();
});

document.body.addEventListener("input", (event) => {
  const target = event.target;
  if (target.dataset.availability) {
    state.availability[target.dataset.availability] = target.checked;
  }
  if (target.dataset.row) {
    const row = state.rows[Number(target.dataset.row)];
    const field = target.dataset.field;
    if (field === "tooth") {
      row[field] = target.value;
    } else {
      const num = Number(target.value);
      row[field] = Number.isFinite(num) ? num : 0;
    }
  }
  if (target.dataset.iprContact) {
    const value = Number(target.value);
    if (Number.isFinite(value) && value > 0) {
      state.clinicalControls.iprContacts[target.dataset.iprContact] = value;
    } else {
      delete state.clinicalControls.iprContacts[target.dataset.iprContact];
    }
  }
  if (target.id === "printEnabled") state.printExport.enabled = target.checked;
  if (target.id === "printFormat") state.printExport.export_format = target.value;
  if (target.id === "printEmail") state.printExport.delivery_email = target.value;
  if (target.id === "modelMaterial") state.printExport.model_material = target.value;
  if (target.id === "thermoformingMaterial") state.printExport.thermoforming_material = target.value;
  if (target.id === "printSafety") state.printExport.safety_acknowledged = target.checked;
  renderAll();
});

document.body.addEventListener("click", (event) => {
  const target = event.target;
  if (target.id === "addStage") {
    state.rows.push({
      stage: maxStage() + 1,
      tooth: "21",
      x: 0.1,
      y: 0,
      z: 0,
      tip: 0,
      torque: 0,
      rotation: 0,
    });
    renderAll();
  }
  if (target.dataset.remove) {
    state.rows.splice(Number(target.dataset.remove), 1);
    renderAll();
  }
});

renderAvailability();
renderAll();
