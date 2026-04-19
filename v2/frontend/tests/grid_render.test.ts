/**
 * `renderSnapshot` translates a Snapshot into calls against a SpriteLayer.
 * The layer interface is minimal (`clear`, `place`) so Phaser-specific code
 * stays out of the testable core.
 */

import { describe, it, expect } from "vitest";

import { renderSnapshot, type SpriteLayer, type PlaceArgs } from "../src/scenes/grid_render";
import type { Snapshot } from "../src/transport/events";

class RecordingLayer implements SpriteLayer {
  clears = 0;
  placed: PlaceArgs[] = [];

  clear(): void {
    this.clears += 1;
  }

  place(args: PlaceArgs): void {
    this.placed.push(args);
  }
}

function snapshot(field: Snapshot["field"], score = 0): Snapshot {
  return { type: "snapshot", score, level: 1, field };
}

function stand(color: number): Snapshot["field"][number][number] {
  return { intention: "STAND", color_index: color };
}

function voidCell(): Snapshot["field"][number][number] {
  return { intention: "VOID", color_index: null };
}

describe("renderSnapshot", () => {
  it("clears the layer exactly once before placing", () => {
    const layer = new RecordingLayer();
    renderSnapshot(snapshot([[voidCell()]]), layer, 32);
    expect(layer.clears).toBe(1);
  });

  it("skips VOID cells", () => {
    const layer = new RecordingLayer();
    renderSnapshot(snapshot([[voidCell(), voidCell()]]), layer, 32);
    expect(layer.placed).toEqual([]);
  });

  it("places one sprite per non-VOID cell", () => {
    const layer = new RecordingLayer();
    renderSnapshot(
      snapshot([
        [stand(0), voidCell(), stand(2)],
        [voidCell(), stand(1), voidCell()],
      ]),
      layer,
      32,
    );
    expect(layer.placed.length).toBe(3);
  });

  it("maps (row, col) to (x = col * size, y = row * size)", () => {
    const layer = new RecordingLayer();
    renderSnapshot(
      snapshot([
        [voidCell(), voidCell()],
        [voidCell(), stand(5)],
      ]),
      layer,
      32,
    );
    expect(layer.placed[0].x).toBe(32);
    expect(layer.placed[0].y).toBe(32);
  });

  it("forwards color_index, intention, and a stable cell id", () => {
    const layer = new RecordingLayer();
    renderSnapshot(
      snapshot([
        [voidCell(), voidCell()],
        [voidCell(), stand(7)],
      ]),
      layer,
      32,
    );
    const p = layer.placed[0];
    expect(p.colorIndex).toBe(7);
    expect(p.intention).toBe("STAND");
    expect(p.id).toBe("1,1");
  });

  it("passes the intention string through for directional bricks", () => {
    const layer = new RecordingLayer();
    renderSnapshot(
      snapshot([[{ intention: "TO_LEFT", color_index: 3 }]]),
      layer,
      32,
    );
    expect(layer.placed[0].intention).toBe("TO_LEFT");
  });
});
