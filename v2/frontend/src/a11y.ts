/**
 * Accessibility settings — independent toggles that layer visual cues on
 * the bricks for players with reduced colour discrimination. State lives
 * in localStorage so it survives reloads; changes broadcast to subscribed
 * listeners (typically the Phaser scene, which regenerates textures and
 * repaints).
 *
 * Flags are additive:
 *   - palette   : swap the hue-based default palette for a luminance-spread
 *                 one (each index sits at a distinct perceived brightness).
 *   - glyphs    : draw a small shape in the top-left corner of each brick
 *                 that differs per colour index (shape carries the match
 *                 signal; colour becomes decorative).
 *   - patterns  : draw a per-colour fill pattern (stripes, dots, etc.) as
 *                 a low-contrast overlay on the brick face.
 */

export interface A11ySettings {
  palette: boolean;
  glyphs: boolean;
  patterns: boolean;
}

const STORAGE_PREFIX = "brickshooter.a11y.";

function storageKey(flag: keyof A11ySettings): string {
  return STORAGE_PREFIX + flag;
}

function readFlag(flag: keyof A11ySettings): boolean {
  return localStorage.getItem(storageKey(flag)) === "1";
}

function writeFlag(flag: keyof A11ySettings, value: boolean): void {
  localStorage.setItem(storageKey(flag), value ? "1" : "0");
}

let current: A11ySettings = {
  palette: readFlag("palette"),
  glyphs: readFlag("glyphs"),
  patterns: readFlag("patterns"),
};

const listeners: Array<(s: A11ySettings) => void> = [];

export function getA11y(): A11ySettings {
  return { ...current };
}

export function setA11y(next: A11ySettings): void {
  current = { ...next };
  writeFlag("palette", current.palette);
  writeFlag("glyphs", current.glyphs);
  writeFlag("patterns", current.patterns);
  for (const l of listeners) l({ ...current });
}

export function onA11yChange(listener: (s: A11ySettings) => void): void {
  listeners.push(listener);
}

/**
 * Short string derived from the active flags. Used as a suffix on cached
 * brick texture keys so Phaser keeps one texture set per setting combo
 * and toggling is just a setTexture() swap, no regeneration latency.
 */
export function a11ySignature(s: A11ySettings): string {
  return `${s.palette ? "p" : "_"}${s.glyphs ? "g" : "_"}${s.patterns ? "t" : "_"}`;
}
