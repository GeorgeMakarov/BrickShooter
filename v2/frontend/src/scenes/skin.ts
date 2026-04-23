/**
 * Programmatic brick skin.
 *
 * Generates a Phaser texture per (intention, colour, a11y) combination at
 * runtime. The look is a raised button: thick light bevel on top/left,
 * thick shadow bevel on bottom/right. Directional variants have a large
 * recessed arrow cut into the surface.
 *
 * Accessibility layers (optional, toggled via the a11y module):
 *   - palette    : switches the colour table; consumed below via the
 *                  `palette` argument, which the caller passes after
 *                  reading getActivePalette().
 *   - glyphs     : per-colour-index shape drawn in the top-left corner
 *                  of every brick, so colour is decorative and shape
 *                  carries the match signal.
 *   - patterns   : per-colour-index fill pattern overlaid on the face,
 *                  clipped by the bevel.
 *
 * Each setting combination produces its own texture key (see
 * `brickTextureKey`), so toggling a flag is just a setTexture swap on
 * every sprite; no per-toggle regeneration cost after the first paint.
 */

import * as Phaser from "phaser";

import { type A11ySettings, a11ySignature } from "../a11y";
import { getActivePalette } from "./colors";

const INTENTIONS = ["STAND", "TO_LEFT", "TO_RIGHT", "TO_UP", "TO_DOWN"] as const;

export function brickTextureKey(intention: string, colorIndex: number, a11y: A11ySettings): string {
  return `brick-${intention}-${colorIndex}-${a11ySignature(a11y)}`;
}

export function generateBrickTextures(scene: Phaser.Scene, size: number, a11y: A11ySettings): void {
  const palette = getActivePalette();
  for (let colorIndex = 0; colorIndex < palette.length; colorIndex++) {
    for (const intention of INTENTIONS) {
      const key = brickTextureKey(intention, colorIndex, a11y);
      if (scene.textures.exists(key)) continue;
      const g = scene.make.graphics({ x: 0, y: 0 }, false);
      drawBrick(g, size, palette[colorIndex], intention, colorIndex, a11y);
      g.generateTexture(key, size, size);
      g.destroy();
    }
  }
}

// ---- drawing -----------------------------------------------------------

function drawBrick(
  g: Phaser.GameObjects.Graphics,
  size: number,
  baseColor: number,
  intention: string,
  colorIndex: number,
  a11y: A11ySettings,
): void {
  const bevel = 3;
  const highlight = shiftBrightness(baseColor, 1.4);
  const shadow = shiftBrightness(baseColor, 0.55);

  // Fill the whole brick with the base colour first. The bevels are
  // drawn on top afterwards, which also clips any pattern overlay to
  // the face region without needing a mask.
  g.fillStyle(baseColor, 1);
  g.fillRect(0, 0, size, size);

  if (a11y.patterns) {
    drawPattern(g, size, bevel, baseColor, colorIndex);
  }

  // Top + left highlight (L-shape meeting at 45° in the inner corners).
  g.fillStyle(highlight, 1);
  fillPolygon(g, [
    [0, 0],
    [size, 0],
    [size - bevel, bevel],
    [bevel, bevel],
    [bevel, size - bevel],
    [0, size],
  ]);

  // Bottom + right shadow.
  g.fillStyle(shadow, 1);
  fillPolygon(g, [
    [size, 0],
    [size, size],
    [0, size],
    [bevel, size - bevel],
    [size - bevel, size - bevel],
    [size - bevel, bevel],
  ]);

  drawArrow(g, size, bevel, baseColor, intention);

  if (a11y.glyphs) {
    drawGlyph(g, size, baseColor, colorIndex);
  }
}

function drawArrow(
  g: Phaser.GameObjects.Graphics,
  size: number,
  bevel: number,
  baseColor: number,
  intention: string,
): void {
  if (intention === "STAND") return;

  const outline = shiftBrightness(baseColor, 0.3);   //!< dark outline — reads as recessed
  const fill = shiftBrightness(baseColor, 0.78);     //!< slightly darker than base

  const inset = bevel + 2; //!< keep arrow inside the button face
  const span = size - 2 * inset;
  const cx = size / 2;
  const cy = size / 2;
  const half = span / 2;

  let tri: Array<[number, number]>;
  switch (intention) {
    case "TO_RIGHT":
      tri = [
        [cx + half,         cy],
        [cx - half * 0.25,  cy - half],
        [cx - half * 0.25,  cy - half * 0.45],
        [cx - half,         cy - half * 0.45],
        [cx - half,         cy + half * 0.45],
        [cx - half * 0.25,  cy + half * 0.45],
        [cx - half * 0.25,  cy + half],
      ];
      break;
    case "TO_LEFT":
      tri = [
        [cx - half,         cy],
        [cx + half * 0.25,  cy - half],
        [cx + half * 0.25,  cy - half * 0.45],
        [cx + half,         cy - half * 0.45],
        [cx + half,         cy + half * 0.45],
        [cx + half * 0.25,  cy + half * 0.45],
        [cx + half * 0.25,  cy + half],
      ];
      break;
    case "TO_DOWN":
      tri = [
        [cx,                cy + half],
        [cx - half,         cy - half * 0.25],
        [cx - half * 0.45,  cy - half * 0.25],
        [cx - half * 0.45,  cy - half],
        [cx + half * 0.45,  cy - half],
        [cx + half * 0.45,  cy - half * 0.25],
        [cx + half,         cy - half * 0.25],
      ];
      break;
    case "TO_UP":
      tri = [
        [cx,                cy - half],
        [cx - half,         cy + half * 0.25],
        [cx - half * 0.45,  cy + half * 0.25],
        [cx - half * 0.45,  cy + half],
        [cx + half * 0.45,  cy + half],
        [cx + half * 0.45,  cy + half * 0.25],
        [cx + half,         cy + half * 0.25],
      ];
      break;
    default:
      return;
  }

  g.fillStyle(outline, 1);
  fillPolygon(g, tri);
  g.fillStyle(fill, 1);
  const shrunk: Array<[number, number]> = tri.map(([x, y]) => [
    cx + (x - cx) * 0.78,
    cy + (y - cy) * 0.78,
  ]);
  fillPolygon(g, shrunk);
}

// ---- accessibility layers ---------------------------------------------

/**
 * Small distinctive shape drawn in the top-left corner. Shape varies per
 * colour index; ink colour is picked black-or-white based on the base's
 * luma so it always contrasts. Sits above the arrow so it isn't hidden
 * on launcher-bound directional bricks.
 */
function drawGlyph(
  g: Phaser.GameObjects.Graphics,
  _size: number,
  baseColor: number,
  colorIndex: number,
): void {
  const box = 10;           //!< glyph bounding box (top-left)
  const pad = 2;
  const x0 = pad;
  const y0 = pad;
  const cx = x0 + box / 2;
  const cy = y0 + box / 2;
  const r = box / 2 - 1;

  const ink = luma(baseColor) < 128 ? 0xffffff : 0x000000;
  g.fillStyle(ink, 1);
  g.lineStyle(1.5, ink, 1);

  switch (colorIndex) {
    case 0: // filled disc
      g.fillCircle(cx, cy, r);
      break;
    case 1: // filled square
      g.fillRect(x0 + 1, y0 + 1, box - 2, box - 2);
      break;
    case 2: // up triangle
      fillPolygon(g, [
        [cx, y0],
        [x0 + box - 1, y0 + box - 1],
        [x0 + 1, y0 + box - 1],
      ]);
      break;
    case 3: // diamond
      fillPolygon(g, [
        [cx, y0],
        [x0 + box - 1, cy],
        [cx, y0 + box - 1],
        [x0 + 1, cy],
      ]);
      break;
    case 4: // X cross
      fillPolygon(g, [[x0, y0 + 2], [x0 + 2, y0], [x0 + box, y0 + box - 2], [x0 + box - 2, y0 + box]]);
      fillPolygon(g, [[x0 + box - 2, y0], [x0 + box, y0 + 2], [x0 + 2, y0 + box], [x0, y0 + box - 2]]);
      break;
    case 5: // horizontal bar
      g.fillRect(x0, cy - 1.5, box, 3);
      break;
    case 6: // plus
      g.fillRect(cx - 1.5, y0, 3, box);
      g.fillRect(x0, cy - 1.5, box, 3);
      break;
    case 7: // down triangle
      fillPolygon(g, [
        [cx, y0 + box - 1],
        [x0 + 1, y0],
        [x0 + box - 1, y0],
      ]);
      break;
    case 8: // hollow square (ring)
      g.fillRect(x0 + 1, y0 + 1, box - 2, box - 2);
      g.fillStyle(baseColor, 1);
      g.fillRect(x0 + 3, y0 + 3, box - 6, box - 6);
      break;
    case 9: // hexagon
      fillPolygon(g, [
        [cx, y0],
        [x0 + box - 1, y0 + box * 0.25],
        [x0 + box - 1, y0 + box * 0.75],
        [cx, y0 + box - 1],
        [x0 + 1, y0 + box * 0.75],
        [x0 + 1, y0 + box * 0.25],
      ]);
      break;
    default:
      g.fillCircle(cx, cy, r);
  }
}

/**
 * Per-colour fill pattern. Drawn right after the base face fill and
 * before the bevels (bevels overwrite the outer rim, so the pattern is
 * visually clipped to the face area without a real mask).
 */
function drawPattern(
  g: Phaser.GameObjects.Graphics,
  size: number,
  bevel: number,
  baseColor: number,
  colorIndex: number,
): void {
  const x0 = bevel;
  const y0 = bevel;
  const w = size - 2 * bevel;
  const h = size - 2 * bevel;

  const baseLuma = luma(baseColor);
  const overlay = baseLuma < 128 ? shiftBrightness(baseColor, 1.7) : shiftBrightness(baseColor, 0.45);
  const alpha = 0.55;

  g.fillStyle(overlay, alpha);

  switch (colorIndex) {
    case 0: // horizontal stripes
      for (let y = y0; y < y0 + h; y += 4) {
        g.fillRect(x0, y, w, 2);
      }
      break;
    case 1: // vertical stripes
      for (let x = x0; x < x0 + w; x += 4) {
        g.fillRect(x, y0, 2, h);
      }
      break;
    case 2: // diagonal / stripes (drawn as short polygons, oversize then clipped by bevel)
      for (let i = -h; i < w + h; i += 4) {
        fillPolygon(g, [
          [x0 + i, y0 + h],
          [x0 + i + 2, y0 + h],
          [x0 + i + 2 + h, y0],
          [x0 + i + h, y0],
        ]);
      }
      break;
    case 3: // diagonal \ stripes
      for (let i = -h; i < w + h; i += 4) {
        fillPolygon(g, [
          [x0 + i, y0],
          [x0 + i + 2, y0],
          [x0 + i + 2 + h, y0 + h],
          [x0 + i + h, y0 + h],
        ]);
      }
      break;
    case 4: // small dots
      for (let y = y0 + 2; y < y0 + h; y += 4) {
        for (let x = x0 + 2; x < x0 + w; x += 4) {
          g.fillCircle(x, y, 1);
        }
      }
      break;
    case 5: // cross-hatch (both diagonals)
      for (let i = -h; i < w + h; i += 5) {
        fillPolygon(g, [
          [x0 + i, y0 + h],
          [x0 + i + 1.5, y0 + h],
          [x0 + i + 1.5 + h, y0],
          [x0 + i + h, y0],
        ]);
        fillPolygon(g, [
          [x0 + i, y0],
          [x0 + i + 1.5, y0],
          [x0 + i + 1.5 + h, y0 + h],
          [x0 + i + h, y0 + h],
        ]);
      }
      break;
    case 6: // checker
      for (let y = y0; y < y0 + h; y += 4) {
        for (let x = x0 + (((y - y0) / 4) % 2 === 0 ? 0 : 4); x < x0 + w; x += 8) {
          g.fillRect(x, y, 4, 4);
        }
      }
      break;
    case 7: // thick horizontal bars
      for (let y = y0 + 2; y < y0 + h; y += 7) {
        g.fillRect(x0, y, w, 3);
      }
      break;
    case 8: // inner frame
      g.fillRect(x0, y0, w, 2);
      g.fillRect(x0, y0 + h - 2, w, 2);
      g.fillRect(x0, y0, 2, h);
      g.fillRect(x0 + w - 2, y0, 2, h);
      break;
    case 9: // large dots
      for (let y = y0 + 3; y < y0 + h; y += 7) {
        for (let x = x0 + 3; x < x0 + w; x += 7) {
          g.fillCircle(x, y, 2);
        }
      }
      break;
    default:
      break;
  }
}

// ---- helpers ----------------------------------------------------------

function fillPolygon(g: Phaser.GameObjects.Graphics, pts: Array<[number, number]>): void {
  g.beginPath();
  g.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) {
    g.lineTo(pts[i][0], pts[i][1]);
  }
  g.closePath();
  g.fillPath();
}

function shiftBrightness(color: number, factor: number): number {
  const r = clamp255(((color >> 16) & 0xff) * factor);
  const gCh = clamp255(((color >> 8) & 0xff) * factor);
  const b = clamp255((color & 0xff) * factor);
  return (r << 16) | (gCh << 8) | b;
}

function clamp255(v: number): number {
  if (v < 0) return 0;
  if (v > 255) return 255;
  return Math.round(v);
}

/** ITU-R BT.601 approximation — good enough for contrast decisions. */
function luma(color: number): number {
  const r = (color >> 16) & 0xff;
  const g = (color >> 8) & 0xff;
  const b = color & 0xff;
  return 0.299 * r + 0.587 * g + 0.114 * b;
}
