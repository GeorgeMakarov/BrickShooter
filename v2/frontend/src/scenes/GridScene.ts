/**
 * Main Phaser scene.
 *
 * Owns:
 *   - the brick sprite grid (one Image per non-VOID cell)
 *   - each sprite's intention + colour_index (to pick the right texture)
 *   - the pointer input on launcher cells (click -> shoot message)
 *   - the transport wiring (snapshot -> repaint; event -> animate)
 *
 * Texture choice follows the server's authoritative intention — never
 * inferred from motion. A brick that moved but is still directional (stuck
 * behind another brick) keeps its arrow; a launcher shift (STAND brick moving
 * one cell) never grows one.
 */

import * as Phaser from "phaser";

import type { Cell, Snapshot } from "../transport/events";
import type { GameSocket } from "../transport/ws_client";
import { colorFor } from "./colors";
import { dispatchEvent, type SceneEffects } from "./event_dispatch";
import { renderSnapshot, type PlaceArgs, type SpriteLayer } from "./grid_render";
import { brickTextureKey, generateBrickTextures } from "./skin";

const FIELD_SIZE = 16;
const PLAY_AREA_START = 3;
const PLAY_AREA_END = 13;
const CELL_SIZE = 32;
const BRICK_SIZE = 30;
const MOVE_DURATION_MS = 80;
const BOARD_BG = 0x0f1b2d;
const PLAY_BORDER = 0xffffff;

export interface GridSceneDeps {
  socket: GameSocket;
  onScore: (total: number) => void;
  /** Silent updates of the current level — fires on every snapshot. */
  onLevel: (level: number) => void;
  /** Celebratory "you cleared level N!" signal — fires only on LevelCleared. */
  onLevelCleared: (level: number) => void;
  onGameOver: (reason: string, won: boolean, level: number, score: number) => void;
}

interface BrickSprite {
  image: Phaser.GameObjects.Image;
  intention: string;
  colorIndex: number;
}

export class GridScene extends Phaser.Scene implements SpriteLayer, SceneEffects {
  private sprites = new Map<string, BrickSprite>();
  private socket!: GameSocket;
  private onScore!: (total: number) => void;
  private onLevel!: (level: number) => void;
  private onLevelCleared!: (level: number) => void;
  private onGameOver!: (reason: string, won: boolean, level: number, score: number) => void;

  constructor() {
    super("GridScene");
  }

  init(data: GridSceneDeps): void {
    this.socket = data.socket;
    this.onScore = data.onScore;
    this.onLevel = data.onLevel;
    this.onLevelCleared = data.onLevelCleared;
    this.onGameOver = data.onGameOver;
  }

  create(): void {
    generateBrickTextures(this, BRICK_SIZE);
    this.cameras.main.setBackgroundColor(BOARD_BG);
    this.drawGridLines();
    this.drawPlayOutline();
    this.wireInput();
    this.socket.onSnapshot((s) => this.applySnapshot(s));
    this.socket.onEvent((e) => dispatchEvent(e, this));
  }

  // --- SpriteLayer (snapshot repaint) --------------------------------

  clear(): void {
    for (const s of this.sprites.values()) s.image.destroy();
    this.sprites.clear();
  }

  place(args: PlaceArgs): void {
    const image = this.add.image(
      args.x + CELL_SIZE / 2,
      args.y + CELL_SIZE / 2,
      brickTextureKey(args.intention, args.colorIndex),
    );
    this.sprites.set(args.id, {
      image,
      intention: args.intention,
      colorIndex: args.colorIndex,
    });
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

  activateBrick(cell: Cell, direction: string): void {
    const sprite = this.sprites.get(cellKey(cell));
    if (!sprite) return;
    sprite.intention = direction;
    sprite.image.setTexture(brickTextureKey(direction, sprite.colorIndex));
  }

  moveBrick(from: Cell, to: Cell): void {
    const sprite = this.sprites.get(cellKey(from));
    if (!sprite) return;
    this.sprites.delete(cellKey(from));
    // If the destination already has a sprite (crosser-shift case: the
    // outermost slot is about to be overwritten by a brick moving in), destroy
    // it — otherwise we leak a stale sprite under the arriving one.
    this.destroySpriteAt(to);
    this.sprites.set(cellKey(to), sprite);
    // Intention is unchanged, but refresh the texture from the tracked
    // intention — covers the case where a previous cross left the sprite with
    // a stale directional texture because its onComplete was cancelled by a
    // later move. The texture always matches the server-authoritative state.
    sprite.image.setTexture(brickTextureKey(sprite.intention, sprite.colorIndex));
    this.tweens.add({
      targets: sprite.image,
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
      const centerX = sprite.image.x;
      const centerY = sprite.image.y;
      this.tweens.add({
        targets: sprite.image,
        scale: 0,
        alpha: 0,
        duration: 220,
        ease: "Cubic.easeIn",
        onComplete: () => sprite.image.destroy(),
      });
      this.emitParticles(centerX, centerY, colour);
    }
  }

  crossBrick(from: Cell, to: Cell, _colorIndex: number): void {
    const sprite = this.sprites.get(cellKey(from));
    if (!sprite) return;
    this.sprites.delete(cellKey(from));
    // Shift events preceding this cross already vacated `to`; guard against
    // edge cases (e.g. resync drift) by destroying whatever's there.
    this.destroySpriteAt(to);
    this.sprites.set(cellKey(to), sprite);
    // Crossers land STAND on the far launcher — set both intention and
    // texture immediately. Doing the texture in onComplete was fragile: a
    // later move in the same burst would whisk the sprite away and the
    // onComplete guard would skip the update, leaving a stale arrow forever.
    sprite.intention = "STAND";
    sprite.image.setTexture(brickTextureKey("STAND", sprite.colorIndex));
    this.tweens.add({
      targets: sprite.image,
      x: to[1] * CELL_SIZE + CELL_SIZE / 2,
      y: to[0] * CELL_SIZE + CELL_SIZE / 2,
      duration: MOVE_DURATION_MS,
      ease: "Linear",
    });
  }

  spawnBrick(cell: Cell, colorIndex: number): void {
    const [r, c] = cell;
    const image = this.add.image(
      c * CELL_SIZE + CELL_SIZE / 2,
      r * CELL_SIZE + CELL_SIZE / 2,
      brickTextureKey("STAND", colorIndex),
    );
    image.setAlpha(0);
    this.sprites.set(cellKey(cell), { image, intention: "STAND", colorIndex });
    this.tweens.add({ targets: image, alpha: 1, duration: 200 });
  }

  updateScore(total: number, _delta: number): void {
    this.onScore(total);
  }

  showLevelCleared(level: number): void {
    this.onLevel(level + 1); // the server has already advanced — keep UI in sync
    this.onLevelCleared(level);
    // Brief on-canvas flash: a banner with "Level N Clear!" fading up and out.
    const banner = this.add.text(
      (FIELD_SIZE * CELL_SIZE) / 2,
      (FIELD_SIZE * CELL_SIZE) / 2,
      `Level ${level} Clear!`,
      { fontSize: "32px", color: "#f1c40f", fontStyle: "bold" },
    );
    banner.setOrigin(0.5);
    banner.setAlpha(0);
    banner.setScale(0.7);
    this.tweens.add({
      targets: banner,
      alpha: 1,
      scale: 1.1,
      duration: 250,
      yoyo: true,
      hold: 500,
      onComplete: () => banner.destroy(),
    });
  }

  showGameOver(reason: string, won: boolean, level: number, score: number): void {
    this.onGameOver(reason, won, level, score);
  }

  resync(): void {
    this.socket.send({ type: "snapshot" });
  }

  // --- internals -----------------------------------------------------

  private applySnapshot(snapshot: Snapshot): void {
    renderSnapshot(snapshot, this, CELL_SIZE);
    this.onScore(snapshot.score);
    this.onLevel(snapshot.level);
  }

  private destroySpriteAt(cell: Cell): void {
    const existing = this.sprites.get(cellKey(cell));
    if (existing) {
      existing.image.destroy();
      this.sprites.delete(cellKey(cell));
    }
  }

  private drawGridLines(): void {
    const g = this.add.graphics();
    g.lineStyle(1, 0xffffff, 0.1);
    const playMin = PLAY_AREA_START * CELL_SIZE;
    const playMax = PLAY_AREA_END * CELL_SIZE;
    for (let i = PLAY_AREA_START + 1; i < PLAY_AREA_END; i++) {
      const p = i * CELL_SIZE;
      g.lineBetween(playMin, p, playMax, p);
      g.lineBetween(p, playMin, p, playMax);
    }
  }

  private drawPlayOutline(): void {
    const g = this.add.graphics();
    g.lineStyle(2, PLAY_BORDER, 0.8);
    g.strokeRect(
      PLAY_AREA_START * CELL_SIZE,
      PLAY_AREA_START * CELL_SIZE,
      (PLAY_AREA_END - PLAY_AREA_START) * CELL_SIZE,
      (PLAY_AREA_END - PLAY_AREA_START) * CELL_SIZE,
    );
  }

  private wireInput(): void {
    this.input.on("pointerdown", (pointer: Phaser.Input.Pointer) => {
      const c = Math.floor(pointer.worldX / CELL_SIZE);
      const r = Math.floor(pointer.worldY / CELL_SIZE);
      if (r < 0 || r >= FIELD_SIZE || c < 0 || c >= FIELD_SIZE) return;
      if (!this.isLauncherCell(r, c)) return;
      this.socket.send({ type: "shoot", cell: [r, c] });
    });
  }

  private emitParticles(x: number, y: number, colour: number): void {
    for (let i = 0; i < 6; i++) {
      const angle = (Math.PI * 2 * i) / 6;
      const particle = this.add.rectangle(x, y, 6, 6, colour);
      this.tweens.add({
        targets: particle,
        x: x + Math.cos(angle) * 30,
        y: y + Math.sin(angle) * 30,
        alpha: 0,
        duration: 400,
        ease: "Cubic.easeOut",
        onComplete: () => particle.destroy(),
      });
    }
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
