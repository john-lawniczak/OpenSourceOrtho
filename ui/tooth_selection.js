// Numbering and input rules shared by the explorer controls and tests.
export const FDI_QUADRANTS = [
  { name: "Upper right", teeth: [18, 17, 16, 15, 14, 13, 12, 11] },
  { name: "Upper left", teeth: [21, 22, 23, 24, 25, 26, 27, 28] },
  { name: "Lower right", teeth: [48, 47, 46, 45, 44, 43, 42, 41] },
  { name: "Lower left", teeth: [31, 32, 33, 34, 35, 36, 37, 38] },
];
export const FDI_TEETH = FDI_QUADRANTS.flatMap(({ teeth }) => teeth.map(String));
const names = ["central incisor", "lateral incisor", "canine", "first premolar",
  "second premolar", "first molar", "second molar", "third molar"];
const quadrants = { 1: "Upper right", 2: "Upper left", 3: "Lower left", 4: "Lower right" };

export function toothName(tooth) {
  const id = String(tooth);
  return FDI_TEETH.includes(id) ? `${quadrants[id[0]]} ${names[Number(id[1]) - 1]}` : "Unknown tooth";
}

export function parseToothSelection(text) {
  const tokens = String(text).trim().split(/[\s,;]+/).filter(Boolean);
  return {
    teeth: [...new Set(tokens.filter((id) => FDI_TEETH.includes(id)))],
    invalid: [...new Set(tokens.filter((id) => !FDI_TEETH.includes(id)))],
  };
}

export function toggleToothSelection(teeth, tooth) {
  const id = String(tooth);
  if (!FDI_TEETH.includes(id)) return [...teeth];
  return teeth.includes(id) ? teeth.filter((item) => item !== id) : [...teeth, id];
}

export function highlightTextColor(hex) {
  const rgb = hex.slice(1).match(/.{2}/g).map((part) => parseInt(part, 16) / 255);
  const linear = rgb.map((v) => v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4);
  const luminance = linear[0] * 0.2126 + linear[1] * 0.7152 + linear[2] * 0.0722;
  return luminance > 0.179 ? "#000000" : "#ffffff";
}
