/**
 * DomainEvent decoder tests.
 *
 * The frames here mirror exactly what `backend.adapters.codec.to_json` produces
 * on the Python side (see v2/tests/test_codec.py). If either side changes the
 * wire shape without updating the other, these assertions fail.
 */

import { describe, it, expect } from "vitest";

import {
  decodeEvent,
  type BrickMatched,
  type BrickMoved,
  type BrickShot,
  type ScoreChanged,
  type StateReverted,
  type GameOver,
} from "../src/transport/events";

describe("decodeEvent", () => {
  it("decodes BrickShot with type narrowing", () => {
    const frame = {
      type: "BrickShot",
      launcher_cell: [5, 2],
      ammo_cell: [5, 2],
      direction: "TO_RIGHT",
    };
    const e = decodeEvent(frame) as BrickShot;
    expect(e.type).toBe("BrickShot");
    expect(e.launcher_cell).toEqual([5, 2]);
    expect(e.direction).toBe("TO_RIGHT");
  });

  it("decodes BrickMoved", () => {
    const e = decodeEvent({
      type: "BrickMoved",
      from_cell: [5, 13],
      to_cell: [5, 12],
    }) as BrickMoved;
    expect(e.type).toBe("BrickMoved");
    expect(e.from_cell).toEqual([5, 13]);
    expect(e.to_cell).toEqual([5, 12]);
  });

  it("decodes BrickMatched preserving cells array", () => {
    const e = decodeEvent({
      type: "BrickMatched",
      cells: [[5, 3], [5, 4], [5, 5]],
      color_index: 2,
    }) as BrickMatched;
    expect(e.type).toBe("BrickMatched");
    expect(e.cells.length).toBe(3);
    expect(e.color_index).toBe(2);
  });

  it("decodes BrickCrossed", () => {
    const e = decodeEvent({
      type: "BrickCrossed",
      from_cell: [5, 12],
      to_cell: [5, 13],
      color_index: 4,
    });
    expect(e.type).toBe("BrickCrossed");
  });

  it("decodes LaunchZoneRefilled", () => {
    const e = decodeEvent({
      type: "LaunchZoneRefilled",
      new_cell: [5, 15],
      color_index: 7,
    });
    expect(e.type).toBe("LaunchZoneRefilled");
  });

  it("decodes ScoreChanged with numeric payload", () => {
    const e = decodeEvent({
      type: "ScoreChanged",
      delta: 30,
      total: 130,
    }) as ScoreChanged;
    expect(e.delta).toBe(30);
    expect(e.total).toBe(130);
  });

  it("decodes StateReverted", () => {
    const e = decodeEvent({
      type: "StateReverted",
      score: 42,
    }) as StateReverted;
    expect(e.score).toBe(42);
  });

  it("decodes GameOver with won flag, level, and score", () => {
    const e = decodeEvent({
      type: "GameOver",
      reason: "No more moves.",
      won: false,
      level: 3,
      score: 240,
    }) as GameOver;
    expect(e.won).toBe(false);
    expect(e.level).toBe(3);
    expect(e.score).toBe(240);
  });

  it("decodes LevelCleared", () => {
    const e = decodeEvent({ type: "LevelCleared", level: 2 });
    expect(e.type).toBe("LevelCleared");
  });

  it("throws when type discriminator is missing", () => {
    expect(() => decodeEvent({ from_cell: [0, 0] })).toThrow(/type/);
  });

  it("throws on unknown type", () => {
    expect(() => decodeEvent({ type: "Teleport" })).toThrow(/unknown/i);
  });

  it("throws on non-object frame", () => {
    expect(() => decodeEvent(null)).toThrow();
    expect(() => decodeEvent("not a frame")).toThrow();
  });
});
