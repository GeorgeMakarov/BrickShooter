/**
 * Palette. Order matches the Python domain's COLOR_NAMES so color_index
 * values round-trip between server and client without a lookup table
 * shipped over the wire.
 */

export const BRICK_COLORS: number[] = [
  0xe53935, //!< red
  0x1e5fd6, //!< blue
  0x8e44ad, //!< purple
  0x4caf50, //!< green    — lighter, clearly separated from cyan in luma
  0xffeb3b, //!< yellow
  0x795548, //!< brown
  0x00acc1, //!< cyan     — deeper teal, clearly below green in luma
  0xff6f00, //!< orange
  0xb0bec5, //!< grey
  0xe91e63, //!< magenta
];

export function colorFor(index: number): number {
  return BRICK_COLORS[index] ?? 0xffffff;
}
