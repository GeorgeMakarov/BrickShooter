/**
 * Palettes. Order matches the Python domain's COLOR_NAMES so color_index
 * values round-trip between server and client without a lookup table
 * shipped over the wire.
 *
 * Two palettes are exported:
 *   - DEFAULT: hue-based, tuned for players with normal colour vision.
 *   - HIGH_CONTRAST: each index sits at a distinct perceived luminance so
 *     adjacent colours on the grid can be told apart by lightness alone
 *     (for players whose hue discrimination is reduced — e.g. age-related
 *     lens yellowing, deuteranopia, tritanopia).
 *
 * Both arrays have ten entries; indexing must stay parallel.
 */

import { getA11y } from "../a11y";

export const BRICK_COLORS_DEFAULT: readonly number[] = [
  0xe53935, //!< red
  0x1e5fd6, //!< blue
  0x8e44ad, //!< purple
  0x4caf50, //!< green
  0xffeb3b, //!< yellow
  0x795548, //!< brown
  0x00acc1, //!< cyan
  0xff6f00, //!< orange
  0xb0bec5, //!< grey
  0xe91e63, //!< magenta
];

/**
 * Luminance-spread palette. Perceived lightness (ITU-R BT.601 luma) of
 * each entry below, so even without hue discrimination the 9 active
 * indices read as distinct brightness steps.
 *
 * Approx luma (/255): red 123, blue 55, purple 82, green 142, yellow 233,
 * brown 66, cyan 185, orange 155, grey 214, magenta 101.
 * Active set 0-8 sorted: 55 (blue) → 66 (brown) → 82 (purple) → 123 (red)
 *   → 142 (green) → 155 (orange) → 185 (cyan) → 214 (grey) → 233 (yellow).
 * Adjacent gaps are 10+ in every case — large enough to separate tiles by
 * brightness alone on an 80-year-old's yellowed lens.
 */
export const BRICK_COLORS_HIGH_CONTRAST: readonly number[] = [
  0xe25050, //!< red       — L≈123
  0x0f3b8a, //!< blue      — L≈55  (darkest)
  0x7232a3, //!< purple    — L≈82
  0x40bf5d, //!< green     — L≈142
  0xfaedaa, //!< yellow    — L≈233 (brightest)
  0x663719, //!< brown     — L≈66
  0x89cdd3, //!< cyan      — L≈185
  0xf18335, //!< orange    — L≈155
  0xd3d7db, //!< grey      — L≈214
  0xc22f84, //!< magenta   — L≈101
];

export function getActivePalette(): readonly number[] {
  return getA11y().palette ? BRICK_COLORS_HIGH_CONTRAST : BRICK_COLORS_DEFAULT;
}

export function colorFor(index: number): number {
  const palette = getActivePalette();
  return palette[index] ?? 0xffffff;
}
