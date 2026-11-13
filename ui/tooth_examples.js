import { FDI_TEETH } from "./tooth_selection.js";

export const TOOTH_EXAMPLES = {
  neutral: "Reference map · simplified tooth shapes and numbering.",
  crowding: "Crowding · some front teeth overlap or sit out of line. Select a tooth number to locate it.",
  spacing: "Spacing · visible gaps between neighboring teeth. Select a tooth number to locate it.",
  "open-bite": "Front open bite · a larger gap between the upper and lower front teeth. Select a tooth number to locate it.",
};

// Illustrative offsets in schematic viewer units (x lateral, y depth, z up).
// These never enter patient scans, inferred motion or treatment-plan state.
export function toothExampleOffsets(example) {
  if (!Object.hasOwn(TOOTH_EXAMPLES, example)) throw new Error("Unknown tooth example");
  return Object.fromEntries(FDI_TEETH.map(tooth => {
    const quadrant = Number(tooth[0]), position = Number(tooth[1]);
    const side = [1, 4].includes(quadrant) ? -1 : 1;
    const offset = { x: 0, y: 0, z: 0 };
    if (example === "crowding" && quadrant >= 3 && position <= 3) {
      offset.x = -side * position * .36;
      offset.y = position % 2 ? .95 : -.95;
    }
    if (example === "spacing") offset.x = side * (.6 + position * .5);
    if (example === "open-bite" && position <= 3) offset.z = (quadrant <= 2 ? 1 : -1) * (4 - position) * .65;
    return [tooth, offset];
  }));
}
