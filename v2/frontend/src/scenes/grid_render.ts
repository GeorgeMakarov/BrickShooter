/**
 * Pure "snapshot → sprite commands" function.
 *
 * The caller provides a `SpriteLayer` (a narrow surface over the rendering
 * backend — Phaser, DOM, whatever). This module has no Phaser dependency so
 * it's trivially testable.
 */

import type { Snapshot } from "../transport/events";

export interface PlaceArgs {
  id: string;
  x: number;
  y: number;
  colorIndex: number;
  intention: string;
}

export interface SpriteLayer {
  clear(): void;
  place(args: PlaceArgs): void;
}

export function renderSnapshot(snapshot: Snapshot, layer: SpriteLayer, cellSize: number): void {
  layer.clear();
  for (let r = 0; r < snapshot.field.length; r++) {
    const row = snapshot.field[r];
    for (let c = 0; c < row.length; c++) {
      const brick = row[c];
      if (brick.intention === "VOID") continue;
      layer.place({
        id: `${r},${c}`,
        x: c * cellSize,
        y: r * cellSize,
        colorIndex: brick.color_index ?? 0,
        intention: brick.intention,
      });
    }
  }
}
