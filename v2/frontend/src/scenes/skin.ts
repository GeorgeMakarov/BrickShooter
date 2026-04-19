/**
 * Programmatic brick skin.
 *
 * Generates a Phaser texture per (intention, colour) combination at runtime.
 * The look is a raised button: thick light bevel on top/left, thick shadow
 * bevel on bottom/right. Directional variants have a large recessed arrow cut
 * into the surface (dark outline + shadow fill — reads as embossed-inward).
 *
 * No bitmap dependency — to reskin, edit the drawing functions in this file.
 */

import * as Phaser from "phaser";

import { BRICK_COLORS } from "./colors";

const INTENTIONS = ["STAND", "TO_LEFT", "TO_RIGHT", "TO_UP", "TO_DOWN"] as const;

export function brickTextureKey(intention: string, colorIndex: number): string {
  return `brick-${intention}-${colorIndex}`;
}

export function generateBrickTextures(scene: Phaser.Scene, size = 30): void {
  for (let colorIndex = 0; colorIndex < BRICK_COLORS.length; colorIndex++) {
    for (const intention of INTENTIONS) {
      const key = brickTextureKey(intention, colorIndex);
      if (scene.textures.exists(key)) continue;
      const g = scene.make.graphics({ x: 0, y: 0 }, false);
      drawBrick(g, size, BRICK_COLORS[colorIndex], intention);
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
): void {
  const bevel = Math.max(3, Math.round(size * 0.15)); //!< ~15% of cell = thick 3D rim
  const highlight = shiftBrightness(baseColor, 1.45);
  const shadow = shiftBrightness(baseColor, 0.55);
  const edge = shiftBrightness(baseColor, 0.35);

  // Outer edge — a 1px hard darker ring so neighbouring bricks don't bleed.
  g.fillStyle(edge, 1);
  g.fillRect(0, 0, size, size);

  // Top + left highlight.
  g.fillStyle(highlight, 1);
  fillPolygon(g, [
    [1, 1],
    [size - 1, 1],
    [size - 1 - bevel, 1 + bevel],
    [1 + bevel, 1 + bevel],
    [1 + bevel, size - 1 - bevel],
    [1, size - 1],
  ]);

  // Bottom + right shadow.
  g.fillStyle(shadow, 1);
  fillPolygon(g, [
    [size - 1, 1],
    [size - 1, size - 1],
    [1, size - 1],
    [1 + bevel, size - 1 - bevel],
    [size - 1 - bevel, size - 1 - bevel],
    [size - 1 - bevel, 1 + bevel],
  ]);

  // Flat centre — the button face.
  g.fillStyle(baseColor, 1);
  g.fillRect(1 + bevel, 1 + bevel, size - 2 - 2 * bevel, size - 2 - 2 * bevel);

  // Directional arrow embossed into the face.
  drawArrow(g, size, bevel, baseColor, intention);
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

  // Arrow points: filled-arrow silhouette with a rectangular tail.
  // Visually matches the v1 NBricks.bmp shapes.
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

  // Dark outline + lighter fill = "pressed into the surface" look.
  g.fillStyle(outline, 1);
  fillPolygon(g, tri);
  g.fillStyle(fill, 1);
  const shrunk: Array<[number, number]> = tri.map(([x, y]) => [
    cx + (x - cx) * 0.78,
    cy + (y - cy) * 0.78,
  ]);
  fillPolygon(g, shrunk);
}

function fillPolygon(g: Phaser.GameObjects.Graphics, pts: Array<[number, number]>): void {
  g.beginPath();
  g.moveTo(pts[0][0], pts[0][1]);
  for (let i = 1; i < pts.length; i++) {
    g.lineTo(pts[i][0], pts[i][1]);
  }
  g.closePath();
  g.fillPath();
}

// ---- colour helpers ----------------------------------------------------

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
