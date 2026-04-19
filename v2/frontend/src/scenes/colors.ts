/**
 * Palette. Order matches the Python domain's COLOR_NAMES so color_index
 * values round-trip between server and client without a lookup table
 * shipped over the wire.
 */

export const BRICK_COLORS: number[] = [
  0xe74c3c, //!< red
  0x2e86de, //!< blue
  0x9b59b6, //!< purple
  0x27ae60, //!< green
  0xf1c40f, //!< yellow
  0x8b4513, //!< brown
  0x00bcd4, //!< cyan
  0xff9800, //!< orange
  0x95a5a6, //!< grey
  0xff00ff, //!< magenta
];

export function colorFor(index: number): number {
  return BRICK_COLORS[index] ?? 0xffffff;
}
