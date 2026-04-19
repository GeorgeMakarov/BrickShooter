/**
 * Main Phaser scene.
 *
 * Owns:
 *   - the brick sprite grid (one Rectangle per non-VOID cell)
 *   - the pointer input on launcher cells (click -> shoot message)
 *   - the transport wiring (snapshot -> repaint; event -> animate)
 *
 * Implements both SpriteLayer (for snapshot repaints) and SceneEffects (for
 * event-driven animations). Keeping them on one class avoids extra indirection
 * at the Phaser boundary.
 */

import Phaser from "phaser";

import type { Cell, Snapshot } from "../transport/events";
import type { GameSocket } from "../transport/ws_client";
import { colorFor } from "./colors";
import { dispatchEvent, type SceneEffects } from "./event_dispatch";
import { renderSnapshot, type PlaceArgs, type SpriteLayer } from "./grid_render";

const FIELD_SIZE = 16;
const PLAY_AREA_START = 3;
const PLAY_AREA_END = 13;
const CELL_SIZE = 32;
const MOVE_DURATION_MS = 80;
const BOARD_BG = 0x0f1b2d;
const PLAY_BORDER = 0xffffff;

export interface GridSceneDeps {
  socket: GameSocket;
  onScore: (total: number) => void;
  onGameOver: (reason: string, won: boolean) => void;
}

export class GridScene extends Phaser.Scene implements SpriteLayer, SceneEffects {
  private sprites = new Map<string, Phaser.GameObjects.Rectangle>();
  private socket!: GameSocket;
  private onScore!: (total: number) => void;
  private onGameOver!: (reason: string, won: boolean) => void;

  constructor() {
    super("GridScene");
  }

  init(data: GridSceneDeps): void {
    this.socket = data.socket;
    this.onScore = data.onScore;
    this.onGameOver = data.onGameOver;
  }

  create(): void {
    // Background.
    this.cameras.main.setBackgroundColor(BOARD_BG);

    // Play-area outline (10x10 inner square).
    const graphics = this.add.graphics();
    graphics.lineStyle(2, PLAY_BORDER, 0.8);
    graphics.strokeRect(
      PLAY_AREA_START * CELL_SIZE,
      PLAY_AREA_START * CELL_SIZE,
      (PLAY_AREA_END - PLAY_AREA_START) * CELL_SIZE,
      (PLAY_AREA_END - PLAY_AREA_START) * CELL_SIZE,
    );

    // Pointer input — single global listener, converts to (r, c) and decides
    // whether the cell is a launcher trigger.
    this.input.on("pointerdown", (pointer: Phaser.Input.Pointer) => {
      const c = Math.floor(pointer.worldX / CELL_SIZE);
      const r = Math.floor(pointer.worldY / CELL_SIZE);
      if (r < 0 || r >= FIELD_SIZE || c < 0 || c >= FIELD_SIZE) return;
      if (!this.isLauncherCell(r, c)) return;
      this.socket.send({ type: "shoot", cell: [r, c] });
    });

    // Wire the transport.
    this.socket.onSnapshot((s) => this.applySnapshot(s));
    this.socket.onEvent((e) => dispatchEvent(e, this));
  }

  // --- SpriteLayer ---------------------------------------------------

  clear(): void {
    for (const s of this.sprites.values()) s.destroy();
    this.sprites.clear();
  }

  place(args: PlaceArgs): void {
    const rect = this.add.rectangle(
      args.x + CELL_SIZE / 2,
      args.y + CELL_SIZE / 2,
      CELL_SIZE - 2,
      CELL_SIZE - 2,
      colorFor(args.colorIndex),
    );
    rect.setStrokeStyle(1, 0xffffff, 0.25);
    this.sprites.set(args.id, rect);
  }

  // --- SceneEffects --------------------------------------------------

  flashLauncher(cell: Cell): void {
    const [r, c] = cell;
    const flash = this.add.rectangle(
      c * CELL_SIZE + CELL_SIZE / 2,
      r * CELL_SIZE + CELL_SIZE / 2,
      CELL_SIZE,
      CELL_SIZE,
      0xffffff,
      0.6,
    );
    this.tweens.add({
      targets: flash,
      alpha: 0,
      duration: 250,
      onComplete: () => flash.destroy(),
    });
  }

  moveBrick(from: Cell, to: Cell): void {
    const sprite = this.sprites.get(cellKey(from));
    if (!sprite) return;
    this.sprites.delete(cellKey(from));
    this.sprites.set(cellKey(to), sprite);
    this.tweens.add({
      targets: sprite,
      x: to[1] * CELL_SIZE + CELL_SIZE / 2,
      y: to[0] * CELL_SIZE + CELL_SIZE / 2,
      duration: MOVE_DURATION_MS,
      ease: "Linear",
    });
  }

  matchCells(cells: Cell[], colorIndex: number): void {
    const colour = colorFor(colorIndex);
    for (const cell of cells) {
      const sprite = this.sprites.get(cellKey(cell));
      if (!sprite) continue;
      this.sprites.delete(cellKey(cell));
      // Particle burst at the sprite's world position.
      const centerX = sprite.x;
      const centerY = sprite.y;
      this.tweens.add({
        targets: sprite,
        scale: 0,
        alpha: 0,
        duration: 220,
        ease: "Cubic.easeIn",
        onComplete: () => sprite.destroy(),
      });
      for (let i = 0; i < 6; i++) {
        const angle = (Math.PI * 2 * i) / 6;
        const particle = this.add.rectangle(centerX, centerY, 6, 6, colour);
        this.tweens.add({
          targets: particle,
          x: centerX + Math.cos(angle) * 30,
          y: centerY + Math.sin(angle) * 30,
          alpha: 0,
          duration: 400,
          ease: "Cubic.easeOut",
          onComplete: () => particle.destroy(),
        });
      }
    }
  }

  crossBrick(from: Cell, to: Cell, _colorIndex: number): void {
    // Visually identical to moveBrick; the colour_index parameter matters
    // when we reconcile the sprite if it's gone missing mid-animation.
    this.moveBrick(from, to);
  }

  spawnBrick(cell: Cell, colorIndex: number): void {
    const [r, c] = cell;
    const rect = this.add.rectangle(
      c * CELL_SIZE + CELL_SIZE / 2,
      r * CELL_SIZE + CELL_SIZE / 2,
      CELL_SIZE - 2,
      CELL_SIZE - 2,
      colorFor(colorIndex),
    );
    rect.setStrokeStyle(1, 0xffffff, 0.25);
    rect.setAlpha(0);
    this.sprites.set(cellKey(cell), rect);
    this.tweens.add({ targets: rect, alpha: 1, duration: 200 });
  }

  updateScore(total: number, _delta: number): void {
    this.onScore(total);
  }

  showGameOver(reason: string, won: boolean): void {
    this.onGameOver(reason, won);
  }

  resync(): void {
    this.socket.send({ type: "snapshot" });
  }

  // --- internals -----------------------------------------------------

  private applySnapshot(snapshot: Snapshot): void {
    renderSnapshot(snapshot, this, CELL_SIZE);
    this.onScore(snapshot.score);
  }

  private isLauncherCell(r: number, c: number): boolean {
    const rowInPlay = r >= PLAY_AREA_START && r < PLAY_AREA_END;
    const colInPlay = c >= PLAY_AREA_START && c < PLAY_AREA_END;
    const onLeftStrip = c === PLAY_AREA_START - 1 && rowInPlay;
    const onRightStrip = c === PLAY_AREA_END && rowInPlay;
    const onTopStrip = r === PLAY_AREA_START - 1 && colInPlay;
    const onBottomStrip = r === PLAY_AREA_END && colInPlay;
    return onLeftStrip || onRightStrip || onTopStrip || onBottomStrip;
  }
}

function cellKey(cell: Cell): string {
  return `${cell[0]},${cell[1]}`;
}
