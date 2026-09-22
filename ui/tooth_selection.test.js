import test from "node:test";
import assert from "node:assert/strict";
import { FDI_TEETH, highlightTextColor, parseToothSelection, toothName, toggleToothSelection } from "./tooth_selection.js";

test("FDI input accepts mixed separators and deduplicates without guessing invalid IDs", () => {
  assert.deepEqual(parseToothSelection("11,12 33;34\n43 44 11"), {
    teeth: ["11", "12", "33", "34", "43", "44"], invalid: [],
  });
  assert.deepEqual(parseToothSelection("11 19 20 49 01 111 11-12 <b>"), {
    teeth: ["11"], invalid: ["19", "20", "49", "01", "111", "11-12", "<b>"],
  });
  assert.deepEqual(parseToothSelection(" , ; \n"), { teeth: [], invalid: [] });
});

test("all 32 permanent teeth have unique valid IDs and correctly named quadrants", () => {
  assert.equal(new Set(FDI_TEETH).size, 32);
  assert.deepEqual(parseToothSelection(FDI_TEETH.join(" ")).invalid, []);
  assert.equal(toothName("11"), "Upper right central incisor");
  assert.equal(toothName("28"), "Upper left third molar");
  assert.equal(toothName("33"), "Lower left canine");
  assert.equal(toothName("44"), "Lower right first premolar");
});

test("toggles preserve other selections and do not mutate input", () => {
  const initial = ["11", "12"];
  assert.deepEqual(toggleToothSelection(initial, 33), ["11", "12", "33"]);
  assert.deepEqual(toggleToothSelection(initial, "11"), ["12"]);
  assert.deepEqual(toggleToothSelection(initial, "19"), initial);
  assert.deepEqual(initial, ["11", "12"]);
});

test("selected number contrast adapts to dark and light highlight colors", () => {
  assert.equal(highlightTextColor("#2563eb"), "#ffffff");
  assert.equal(highlightTextColor("#facc15"), "#000000");
  assert.equal(highlightTextColor("#ffffff"), "#000000");
  assert.equal(highlightTextColor("#000000"), "#ffffff");
});
