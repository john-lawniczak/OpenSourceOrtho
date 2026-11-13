import test from "node:test";
import assert from "node:assert/strict";
import { FDI_TEETH, universalToothNumber, highlightTextColor, parseToothSelection, toothName, toggleToothSelection } from "./tooth_selection.js";

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


test("FDI and Universal numbers distinguish molars from front teeth", () => {
  assert.equal(universalToothNumber("18"), 1);
  assert.equal(universalToothNumber("17"), 2);
  assert.equal(universalToothNumber("21"), 9);
  assert.equal(universalToothNumber("22"), 10);
  assert.equal(universalToothNumber("31"), 24);
  assert.equal(universalToothNumber("48"), 32);
  assert.equal(universalToothNumber("20"), null);
  assert.deepEqual(FDI_TEETH.map(universalToothNumber).sort((a, b) => a - b), Array.from({ length: 32 }, (_, i) => i + 1));
});

test("explicit FDI and US number selection round-trips all 32 positions", async () => {
  const { toothFromNumber, universalToothNumber, FDI_TEETH } = await import("./tooth_selection.js");
  for (const id of FDI_TEETH) {
    assert.equal(toothFromNumber(id, "FDI"), id);
    assert.equal(toothFromNumber(universalToothNumber(id), "US"), id);
  }
  for (const value of ["", "abc", "1.5", "0", "99"]) assert.equal(toothFromNumber(value, "FDI"), null);
});

test("plan note tags accept explicit FDI mentions with punctuation and deduplicate", async () => {
  const { parseToothMentions } = await import("./tooth_selection.js");
  assert.deepEqual(parseToothMentions("Focus on @12 and @22.\n- Repair #31; compare (@12), **#48**."), ["12", "22", "31", "48"]);
  assert.deepEqual(parseToothMentions("@12/#22"), ["12"]); // The slash-prefixed token could be a URL fragment.
  assert.deepEqual(parseToothMentions(FDI_TEETH.map(id => `@${id}`).join(" ")), FDI_TEETH);
});

test("plan note tags reject ordinary numbers and partial or invalid tokens", async () => {
  const { parseToothMentions } = await import("./tooth_selection.js");
  assert.deepEqual(parseToothMentions("12 22 31 @1 @123 #310 @19 #49 @012 #12abc @22_2 @12.5 name@12.com name#22 @12.com #123abc @@12 ##22 /#31"), []);
  assert.deepEqual(parseToothMentions("(#11). @22! #31?"), ["11", "22", "31"]);
});
