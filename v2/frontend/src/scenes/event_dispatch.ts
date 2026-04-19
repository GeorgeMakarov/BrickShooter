/**
 * Event → scene-effect dispatcher.
 *
 * Every DomainEvent variant maps to exactly one SceneEffects method. The
 * dispatcher is pure logic — no Phaser, no DOM. The Phaser adapter
 * implements SceneEffects with tweens, particle emitters, etc.
 *
 * Switch covers every variant of DomainEvent; the `never`-typed default
 * makes TypeScript flag a missing case if a new event is added.
 */

import type { Cell, DomainEvent } from "../transport/events";

export interface SceneEffects {
  flashLauncher(cell: Cell): void;
  /** Update a brick's intention (texture, etc.) when a shot activates it. */
  activateBrick(cell: Cell, direction: string): void;
  moveBrick(from: Cell, to: Cell): void;
  matchCells(cells: Cell[], colorIndex: number): void;
  crossBrick(from: Cell, to: Cell, colorIndex: number): void;
  spawnBrick(cell: Cell, colorIndex: number): void;
  updateScore(total: number, delta: number): void;
  showLevelCleared(level: number): void;
  showGameOver(reason: string, won: boolean, level: number, score: number): void;
  resync(): void;
}

export function dispatchEvent(event: DomainEvent, effects: SceneEffects): void {
  switch (event.type) {
    case "BrickShot":
      effects.flashLauncher(event.launcher_cell);
      effects.activateBrick(event.ammo_cell, event.direction);
      return;
    case "BrickMoved":
      effects.moveBrick(event.from_cell, event.to_cell);
      return;
    case "BrickMatched":
      effects.matchCells(event.cells, event.color_index);
      return;
    case "BrickCrossed":
      effects.crossBrick(event.from_cell, event.to_cell, event.color_index);
      return;
    case "LaunchZoneRefilled":
      effects.spawnBrick(event.new_cell, event.color_index);
      return;
    case "ScoreChanged":
      effects.updateScore(event.total, event.delta);
      return;
    case "StateReverted":
      effects.resync();
      return;
    case "LevelCleared":
      effects.showLevelCleared(event.level);
      return;
    case "GameOver":
      effects.showGameOver(event.reason, event.won, event.level, event.score);
      return;
    default: {
      const exhaustive: never = event;
      throw new Error(`unhandled event: ${JSON.stringify(exhaustive)}`);
    }
  }
}
