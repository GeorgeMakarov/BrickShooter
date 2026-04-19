/**
 * `dispatchEvent` routes each DomainEvent variant to the right SceneEffects
 * method. The scene-effects interface is minimal and abstract so the Phaser
 * adapter stays out of the pure test path.
 */

import { describe, it, expect } from "vitest";

import { dispatchEvent, type SceneEffects } from "../src/scenes/event_dispatch";
import type { DomainEvent } from "../src/transport/events";

class RecordingEffects implements SceneEffects {
  public calls: string[] = [];
  public args: Record<string, unknown[]> = {};

  private record(name: string, ...args: unknown[]): void {
    this.calls.push(name);
    (this.args[name] ??= []).push(...args);
  }

  flashLauncher(cell: [number, number]): void { this.record("flashLauncher", cell); }
  activateBrick(cell: [number, number], direction: string): void { this.record("activateBrick", cell, direction); }
  moveBrick(from: [number, number], to: [number, number]): void { this.record("moveBrick", from, to); }
  matchCells(cells: [number, number][], color: number): void { this.record("matchCells", cells, color); }
  crossBrick(from: [number, number], to: [number, number], color: number): void { this.record("crossBrick", from, to, color); }
  spawnBrick(cell: [number, number], color: number): void { this.record("spawnBrick", cell, color); }
  updateScore(total: number, delta: number): void { this.record("updateScore", total, delta); }
  showLevelCleared(level: number): void { this.record("showLevelCleared", level); }
  showGameOver(reason: string, won: boolean, level: number, score: number): void {
    this.record("showGameOver", reason, won, level, score);
  }
  resync(): void { this.record("resync"); }
}

function dispatch(event: DomainEvent) {
  const fx = new RecordingEffects();
  dispatchEvent(event, fx);
  return fx;
}

describe("dispatchEvent", () => {
  it("BrickShot -> flashLauncher + activateBrick(ammo_cell, direction)", () => {
    const fx = dispatch({ type: "BrickShot", launcher_cell: [3, 2], ammo_cell: [3, 2], direction: "TO_RIGHT" });
    expect(fx.calls).toEqual(["flashLauncher", "activateBrick"]);
    expect(fx.args.flashLauncher).toEqual([[3, 2]]);
    expect(fx.args.activateBrick).toEqual([[3, 2], "TO_RIGHT"]);
  });

  it("BrickMoved -> moveBrick(from, to)", () => {
    const fx = dispatch({ type: "BrickMoved", from_cell: [5, 13], to_cell: [5, 12] });
    expect(fx.calls).toEqual(["moveBrick"]);
    expect(fx.args.moveBrick).toEqual([[5, 13], [5, 12]]);
  });

  it("BrickMatched -> matchCells(cells, color)", () => {
    const fx = dispatch({ type: "BrickMatched", cells: [[5, 3], [5, 4], [5, 5]], color_index: 2 });
    expect(fx.calls).toEqual(["matchCells"]);
    expect(fx.args.matchCells).toEqual([[[5, 3], [5, 4], [5, 5]], 2]);
  });

  it("BrickCrossed -> crossBrick(from, to, color)", () => {
    const fx = dispatch({ type: "BrickCrossed", from_cell: [5, 12], to_cell: [5, 13], color_index: 4 });
    expect(fx.calls).toEqual(["crossBrick"]);
    expect(fx.args.crossBrick).toEqual([[5, 12], [5, 13], 4]);
  });

  it("LaunchZoneRefilled -> spawnBrick(new_cell, color)", () => {
    const fx = dispatch({ type: "LaunchZoneRefilled", new_cell: [5, 15], color_index: 7 });
    expect(fx.calls).toEqual(["spawnBrick"]);
    expect(fx.args.spawnBrick).toEqual([[5, 15], 7]);
  });

  it("ScoreChanged -> updateScore(total, delta)", () => {
    const fx = dispatch({ type: "ScoreChanged", delta: 30, total: 130 });
    expect(fx.calls).toEqual(["updateScore"]);
    expect(fx.args.updateScore).toEqual([130, 30]);
  });

  it("StateReverted -> resync (client will request a snapshot)", () => {
    const fx = dispatch({ type: "StateReverted", score: 42 });
    expect(fx.calls).toEqual(["resync"]);
  });

  it("LevelCleared -> showLevelCleared(level)", () => {
    const fx = dispatch({ type: "LevelCleared", level: 3 });
    expect(fx.calls).toEqual(["showLevelCleared"]);
    expect(fx.args.showLevelCleared).toEqual([3]);
  });

  it("GameOver -> showGameOver(reason, won, level, score)", () => {
    const fx = dispatch({ type: "GameOver", reason: "No more moves.", won: false, level: 3, score: 240 });
    expect(fx.calls).toEqual(["showGameOver"]);
    expect(fx.args.showGameOver).toEqual(["No more moves.", false, 3, 240]);
  });
});
