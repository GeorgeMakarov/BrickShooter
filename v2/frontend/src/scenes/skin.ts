/**
 * Programmatic brick skin.
 *
 * Generates a Phaser texture per (intention, colour) combination at runtime.
 * Keeps the look decoupled from any bitmap — change this file to change the
 * skin; no assets to reload.
 *
 * Each brick is drawn as a raised button: base fill, lighter bevel on
 * top/left, darker bevel on bottom/right, and (for directional bricks) a
 * white arrow overlay pointing the way the brick is heading.
 */

import * as Phaser from "phaser";

import { BRICK_COLORS } from "./colors";

const INTENTIONS = ["STAND", "TO_LEFT", "TO_RIGHT", "TO_UP", "TO_DOWN"] as const;
export type Intention = (typeof INTENTIONS)[number];

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

function drawBrick(g: Phaser.GameObjects.Graphics, size: number, baseColor: number, intention: string): void {
  const bevel = 3;
  const highlight = shiftBrightness(baseColor, 1.35);
  const shadow = shiftBrightness(baseColor, 0.65);

  // Base fill.
  g.fillStyle(baseColor, 1);
  g.fillRect(0, 0, size, size);

  // Top + left highlight (light bevel).
  g.fillStyle(highlight, 1);
  g.fillRect(0, 0, size, bevel);                //!< top edge
  g.fillRect(0, 0, bevel, size);                //!< left edge

  // Bottom + right shadow (dark bevel).
  g.fillStyle(shadow, 1);
  g.fillRect(0, size - bevel, size, bevel);     //!< bottom edge
  g.fillRect(size - bevel, 0, bevel, size);     //!< right edge

  // Corner mitres: keep the top-right and bottom-left from looking wrong
  // where highlight and shadow meet. Draw small dark/light triangles.
  g.fillStyle(shadow, 1);
  g.fillTriangle(size - bevel, 0, size, 0, size, bevel);          //!< top-right corner (shadowed)
  g.fillStyle(highlight, 1);
  g.fillTriangle(0, size - bevel, bevel, size, 0, size);          //!< bottom-left corner (highlit)

  // Arrow overlay for directional bricks.
  drawArrow(g, size, intention);
}

function drawArrow(g: Phaser.GameObjects.Graphics, size: number, intention: string): void {
  const cx = size / 2;
  const cy = size / 2;
  const s = size * 0.22; //!< half-length of the arrow
  g.fillStyle(0xffffff, 0.92);
  switch (intention) {
    case "TO_LEFT":
      g.fillTriangle(cx - s, cy, cx + s, cy - s, cx + s, cy + s);
      break;
    case "TO_RIGHT":
      g.fillTriangle(cx - s, cy - s, cx - s, cy + s, cx + s, cy);
      break;
    case "TO_UP":
      g.fillTriangle(cx, cy - s, cx - s, cy + s, cx + s, cy + s);
      break;
    case "TO_DOWN":
      g.fillTriangle(cx - s, cy - s, cx + s, cy - s, cx, cy + s);
      break;
    default:
      // STAND: no overlay.
      return;
  }
}

function shiftBrightness(color: number, factor: number): number {
  const r = clamp255(((color >> 16) & 0xff) * factor);
  const g = clamp255(((color >> 8) & 0xff) * factor);
  const b = clamp255((color & 0xff) * factor);
  return (r << 16) | (g << 8) | b;
}

function clamp255(v: number): number {
  if (v < 0) return 0;
  if (v > 255) return 255;
  return Math.round(v);
}
