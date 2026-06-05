import { askPlanAssistant, el, maxStage, state } from "./state.js";
import { demoInitialOffsets, syntheticCrowdingRows } from "./demo.js";
import { recenterViewer, renderAll, renderAvailability, renderChat, setDimension, zoomViewer } from "./render.js";
import { planJson } from "./plan.js";

const savedTheme = localStorage.getItem("orthoplan-theme");
if (savedTheme === "dark") state.theme = "dark";

el("themeToggle").addEventListener("click", () => {
  state.theme = state.theme === "dark" ? "light" : "dark";
  localStorage.setItem("orthoplan-theme", state.theme);
  renderAll();
});

document.querySelectorAll(".mode-choice").forEach((button) => {
  button.addEventListener("click", () => {
    state.userMode = button.dataset.userMode;
    state.activeStep = state.userMode === "simple" ? "simple" : "upload";
    document.querySelectorAll(".mode-choice").forEach((item) => item.classList.remove("is-active"));
    button.classList.add("is-active");
    renderAll();
  });
});

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
  state.useDemoMeshes = false;
  el("uploadLabel").textContent = state.file ? state.file.name : "Choose STL file";
  renderAll();
});

el("simpleStlFile").addEventListener("change", (event) => {
  state.file = event.target.files[0] || null;
  state.demoInitialOffsets = {};
  state.useDemoMeshes = false;
  el("simpleUploadLabel").textContent = state.file ? state.file.name : "Choose your STL";
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
  if (target.id === "simpleGoal") state.simpleGoal = target.value;
  if (target.id === "simpleAcknowledged") state.simpleAcknowledged = target.checked;
  if (target.id === "chatProvider") state.chat.provider = target.value;
  if (target.id === "chatModel") state.chat.model = target.value;
  if (target.id === "chatScope") state.chat.contextScope = target.value;
  if (target.id === "chatInput") state.chat.input = target.value;
  if (target.id === "chatApiKey") state.chat.apiKeyPresent = Boolean(target.value.trim());
  if (target.id === "agentAccessEnabled") state.chat.agentAccessEnabled = target.checked;
  if (target.id === "agentEndpoint") state.chat.agentEndpoint = target.value;
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
  if (target.id === "loadDemo") {
    loadSyntheticDemo();
  }
  if (target.id === "simpleReview") {
    if (!state.simpleAcknowledged) return;
    state.activeStep = "review";
    state.view = "overlay";
    renderAll();
  }
  if (target.id === "sendChat") {
    sendChatMessage();
  }
  if (target.id === "zoomIn") zoomViewer(0.83);
  if (target.id === "zoomOut") zoomViewer(1.2);
  if (target.id === "zoomReset") recenterViewer();
  if (target.dataset.remove) {
    state.rows.splice(Number(target.dataset.remove), 1);
    renderAll();
  }
});

function loadSyntheticDemo() {
  state.userMode = "simple";
  state.simpleAcknowledged = true;
  state.simpleGoal = "crowding";
  state.demoInitialOffsets = demoInitialOffsets;
  state.useDemoMeshes = true;
  state.rows = syntheticCrowdingRows(12);
  state.file = null;
  state.view = "overlay";
  state.activeStep = "review";
  el("planTitle").value = "Educational crowding demo";
  el("planId").value = "synthetic-crowding-demo";
  el("wearInterval").value = "30";
  el("exaggeration").value = "12";
  el("simpleGoal").value = "crowding";
  el("simpleAcknowledged").checked = true;
  renderAll();
}

async function sendChatMessage() {
  const message = state.chat.input.trim();
  if (!message || state.chat.busy) return;
  state.chat.busy = true;
  state.chat.status = "Reviewing the scoped plan context...";
  state.chat.messages.push({ role: "user", content: message });
  el("chatInput").value = "";
  state.chat.input = "";
  renderChat();
  try {
    // The API key is read straight from the DOM at send time so it is never
    // held in app state or persisted - only transmitted on an explicit "Ask AI".
    const apiKey = el("chatApiKey").value.trim();
    const result = await askPlanAssistant({
      plan: planJson(),
      message,
      provider: state.chat.provider,
      model: state.chat.model,
      context_scope: state.chat.contextScope,
      api_key: apiKey || undefined,
      endpoint: state.chat.agentEndpoint.trim() || undefined,
      share_acknowledged: state.chat.agentAccessEnabled,
    });
    if (result.ok === false) {
      state.chat.messages.push({
        role: "assistant",
        content: (result.errors || ["AI chat is not available."]).join(" "),
      });
      state.chat.status = "Connector unavailable";
    } else {
      const assistant = [...result.session.messages].reverse().find((item) => item.role === "assistant");
      state.chat.messages.push({
        role: "assistant",
        content: assistant?.content || "No answer returned.",
      });
      state.chat.status = `${result.session.connector.label} · ${result.session.context_scope.name}`;
    }
  } catch (error) {
    state.chat.messages.push({ role: "assistant", content: error.message });
    state.chat.status = "Chat request failed";
  } finally {
    state.chat.busy = false;
    renderChat();
  }
}

renderAvailability();
renderAll();
