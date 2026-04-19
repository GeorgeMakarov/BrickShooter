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

import type { Sfx } from "../audio/sfx";
import type { Cell, Snapshot } from "../transport/events";
import type { GameSocket } from "../transport/ws_client";
import { BRICK_COLORS, colorFor } from "./colors";
import { dispatchEvent, type SceneEffects } from "./event_dispatch";
import { renderSnapshot, type PlaceArgs, type SpriteLayer } from "./grid_render";
import { brickTextureKey, generateBrickTextures } from "./skin";

const FIELD_SIZE = 16;
const PLAY_AREA_START = 3;
const PLAY_AREA_END = 13;
const CELL_SIZE = 32;
const BRICK_SIZE = 30;
const MOVE_DURATION_MS = 120;
const BOARD_BG = 0x0f1b2d;
const PLAY_BORDER = 0xffffff;

export interface GridSceneDeps {
  socket: GameSocket;
  sfx: Sfx;
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
  /** Active halo sprite if the brick is in flight (attach + destroy are
   *  managed by attachMotionFx / the move tween / matchCells). */
  halo?: Phaser.GameObjects.Image | null;
}

export class GridScene extends Phaser.Scene implements SpriteLayer, SceneEffects {
  private sprites = new Map<string, BrickSprite>();
  private socket!: GameSocket;
  private sfx!: Sfx;
  private onScore!: (total: number) => void;
  private onLevel!: (level: number) => void;
  private onLevelCleared!: (level: number) => void;
  private onGameOver!: (reason: string, won: boolean, level: number, score: number) => void;

  /** Centroids of every match in the current score pass — averaged on the
   *  following `updateScore` so the +N popup lands where the work happened. */
  private pendingMatchCentroids: Array<{ x: number; y: number }> = [];
  /** Number of resolution passes since the last shot that produced a match.
   *  Chain >= 2 means the shot's follow-on moves triggered additional matches. */
  private chainDepth = 0;

  constructor() {
    super("GridScene");
  }

  init(data: GridSceneDeps): void {
    this.socket = data.socket;
    this.sfx = data.sfx;
    this.onScore = data.onScore;
    this.onLevel = data.onLevel;
    this.onLevelCleared = data.onLevelCleared;
    this.onGameOver = data.onGameOver;
  }

  create(): void {
    generateBrickTextures(this, BRICK_SIZE);
    this.generateParticleTexture();
    this.generateHaloTexture();
    this.cameras.main.setBackgroundColor(BOARD_BG);
    this.drawGridLines();
    this.drawPlayOutline();

    this.wireInput();
    this.socket.onSnapshot((s) => this.applySnapshot(s));
    this.socket.onEvent((e) => dispatchEvent(e, this));
  }

  /**
   * 12x12 white disc — used as the base texture for all particle emitters.
   * Tinted at emit-time so one texture serves every brick colour.
   */
  private generateParticleTexture(): void {
    if (this.textures.exists("particle")) return;
    const g = this.make.graphics({ x: 0, y: 0 }, false);
    g.fillStyle(0xffffff, 1);
    g.fillCircle(6, 6, 6);
    g.generateTexture("particle", 12, 12);
    g.destroy();
  }

  /**
   * 64x64 radial-gradient halo texture used for neon ammo glow. Built by
   * stacking many low-alpha circles of decreasing radius — gives a smooth
   * falloff without the stochastic noise of Phaser's Glow filter.
   * Tint is applied per-sprite at use time.
   */
  private generateHaloTexture(): void {
    if (this.textures.exists("halo")) return;
    const size = 64;
    const g = this.make.graphics({ x: 0, y: 0 }, false);
    const steps = 24;
    for (let i = 0; i < steps; i++) {
      const t = i / steps;
      // Quadratic falloff looks more like neon bleed than a linear one.
      const alpha = (1 - t) * (1 - t) * 0.09;
      const radius = (size / 2) * (1 - t * 0.92) + 1;
      g.fillStyle(0xffffff, alpha);
      g.fillCircle(size / 2, size / 2, radius);
    }
    g.generateTexture("halo", size, size);
    g.destroy();
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
    // BrickShot is the "user action" boundary — reset chain state.
    this.chainDepth = 0;
    this.pendingMatchCentroids.length = 0;
    this.sfx.playShot();

    const [r, c] = cell;
    const cx = c * CELL_SIZE + CELL_SIZE / 2;
    const cy = r * CELL_SIZE + CELL_SIZE / 2;

    // Radial glow: a circle that scales up from 0.4 to ~2.2 while fading out.
    const glow = this.add.circle(cx, cy, CELL_SIZE / 2, 0xffffff, 0.5);
    glow.setScale(0.4);
    this.tweens.add({
      targets: glow,
      scale: 2.2,
      alpha: 0,
      duration: 300,
      ease: "Cubic.easeOut",
      onComplete: () => glow.destroy(),
    });

    // A few sparkle particles shooting outward from the launcher cell.
    const sparkle = this.add.particles(cx, cy, "particle", {
      speed: { min: 60, max: 140 },
      angle: { min: 0, max: 360 },
      scale: { start: 0.6, end: 0 },
      alpha: { start: 1, end: 0 },
      lifespan: 300,
      quantity: 0,
      tint: 0xffffff,
    });
    sparkle.explode(6);
    this.time.delayedCall(400, () => sparkle.destroy());
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

    // BrickMoved events can stack faster than the 120ms tween when the shot
    // traverses several cells. Kill any in-flight tweens on the sprite and
    // destroy its previous halo so we always have at most one live set of
    // motion effects per sprite — otherwise we'd leak a visible trail of
    // halos at every cell the brick already passed through.
    this.tweens.killTweensOf(sprite.image);
    if (sprite.halo) {
      this.tweens.killTweensOf(sprite.halo);
      sprite.halo.destroy();
      sprite.halo = null;
    }
    // The blur filter from the previous move might still be attached — clear
    // before re-applying below.
    this.clearMotionFx(sprite.image);

    // Directional motion (an in-flight shot, not a launcher-queue shift):
    //  - apply a Gaussian blur filter aligned with the travel axis (real
    //    motion blur on the sprite itself)
    //  - spawn a pre-baked halo sprite behind the brick, tweened alongside
    //    it — gives a clean neon look that Phaser's stochastic Glow
    //    filter can't match on small sprites.
    const targetX = to[1] * CELL_SIZE + CELL_SIZE / 2;
    const targetY = to[0] * CELL_SIZE + CELL_SIZE / 2;
    const fx = this.attachMotionFx(
      sprite.image,
      sprite.intention,
      sprite.colorIndex,
      targetX,
      targetY,
    );
    sprite.halo = fx.halo;

    this.tweens.add({
      targets: sprite.image,
      x: targetX,
      y: targetY,
      duration: MOVE_DURATION_MS,
      ease: "Linear",
      onComplete: () => {
        if (sprite.image.active && sprite.image.filters) {
          for (const filter of fx.filters) {
            sprite.image.filters.external.remove(filter);
          }
        }
        if (sprite.halo === fx.halo) {
          sprite.halo?.destroy();
          sprite.halo = null;
        }
      },
    });
  }

  /**
   * Attach motion effects to an in-flight brick:
   *  - Gaussian blur filter on the sprite itself (real per-axis motion blur)
   *  - Halo sprite behind the brick (neon glow); tweened alongside the
   *    brick via a fresh tween so both arrive at the destination together
   *
   * Returns the filter controllers (for removal on move complete) plus the
   * halo reference (for destroy on move complete OR early death in match).
   */
  private attachMotionFx(
    image: Phaser.GameObjects.Image,
    intention: string,
    colorIndex: number,
    targetX: number,
    targetY: number,
  ): { filters: Phaser.Filters.Blur[]; halo: Phaser.GameObjects.Image | null } {
    if (intention === "STAND" || intention === "VOID") return { filters: [], halo: null };

    if (!image.filters) image.enableFilters();
    const external = image.filters!.external;
    const horizontal = intention === "TO_LEFT" || intention === "TO_RIGHT";
    const blur = external.addBlur(
      /* quality */ 1,
      /* x */ horizontal ? 4 : 0,
      /* y */ horizontal ? 0 : 4,
      /* strength */ 1,
      /* colour */ 0xffffff,
      /* steps */ 4,
    );

    const halo = this.add.image(image.x, image.y, "halo");
    // Tint to the brick's own colour — the bright additive blend lifts the
    // hue well above the brick body, so it reads as "this brick's energy"
    // rather than merging with the sprite.
    halo.setTint(colorFor(colorIndex));
    halo.setBlendMode(Phaser.BlendModes.ADD);
    halo.setScale(1.1);
    halo.setDepth(image.depth - 1); // sit behind the brick
    // Track the brick's position by running a parallel tween with the same
    // duration and easing. The movement tween above will settle at the same
    // moment.
    this.tweens.add({
      targets: halo,
      x: targetX,
      y: targetY,
      duration: MOVE_DURATION_MS,
      ease: "Linear",
    });

    return { filters: [blur], halo };
  }

  /** Remove every external filter on an Image. Safe to call on sprites
   *  without filters enabled. Used by matchCells to clean up a moving
   *  sprite that's about to die — otherwise the halo blur would wash out
   *  the match particles. Halo sprites are per-brick and tracked via the
   *  attach return; they don't need clean-up here (they self-destruct
   *  on their own tween's onComplete as they chase the dying brick). */
  private clearMotionFx(image: Phaser.GameObjects.Image): void {
    if (!image.filters) return;
    image.filters.external.clear();
  }

  matchCells(cells: Cell[], colorIndex: number): void {
    const colour = colorFor(colorIndex);
    // Track the group's centroid so the +N popup can land here on the next
    // ScoreChanged. Averaged later with any other groups cleared in the same
    // pass.
    let sumX = 0;
    let sumY = 0;
    for (const cell of cells) {
      const sprite = this.sprites.get(cellKey(cell));
      // Burst at the cell's *logical* world centre, not the sprite's current
      // tween-interpolated position — a just-arrived ammo brick may still be
      // mid-move when the match fires, and reading sprite.image.x/y would put
      // the burst somewhere along its flight path instead of at the match.
      const centerX = cell[1] * CELL_SIZE + CELL_SIZE / 2;
      const centerY = cell[0] * CELL_SIZE + CELL_SIZE / 2;
      sumX += centerX;
      sumY += centerY;
      if (sprite) {
        this.sprites.delete(cellKey(cell));
        // Snap the sprite to the cell centre first, then shrink+fade it out,
        // so its visual disappearance is co-located with the burst. Drop any
        // in-flight motion effects so the match particles aren't washed out
        // by a lingering glow — killing the move tween below wouldn't fire
        // its onComplete.
        sprite.image.x = centerX;
        sprite.image.y = centerY;
        this.tweens.killTweensOf(sprite.image);
        this.clearMotionFx(sprite.image);
        if (sprite.halo) {
          this.tweens.killTweensOf(sprite.halo);
          sprite.halo.destroy();
          sprite.halo = null;
        }
        this.tweens.add({
          targets: sprite.image,
          scale: 0,
          alpha: 0,
          duration: 220,
          ease: "Cubic.easeIn",
          onComplete: () => sprite.image.destroy(),
        });
      }
      this.emitMatchBurst(centerX, centerY, colour);
    }
    this.pendingMatchCentroids.push({ x: sumX / cells.length, y: sumY / cells.length });
    this.sfx.playMatch(cells.length);

    // Shake the camera when a big group lands, scaled to group size. Clamped
    // so a huge match doesn't make the game unplayable.
    if (cells.length >= 5) {
      const intensity = Math.min(0.004 + 0.0015 * (cells.length - 4), 0.015);
      const duration = Math.min(120 + 20 * (cells.length - 4), 260);
      this.cameras.main.shake(duration, intensity);
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

  updateScore(total: number, delta: number): void {
    this.onScore(total);
    if (this.pendingMatchCentroids.length > 0 && delta > 0) {
      const { x, y } = this.averagePending();
      this.spawnScorePopup(x, y, delta);
      this.chainDepth += 1;
      if (this.chainDepth >= 2) {
        this.spawnComboPopup(x, y, this.chainDepth);
      }
      this.pendingMatchCentroids.length = 0;
    }
  }

  private averagePending(): { x: number; y: number } {
    const n = this.pendingMatchCentroids.length;
    let x = 0;
    let y = 0;
    for (const p of this.pendingMatchCentroids) {
      x += p.x;
      y += p.y;
    }
    return { x: x / n, y: y / n };
  }

  private spawnScorePopup(x: number, y: number, delta: number): void {
    const text = this.add.text(x, y, `+${delta}`, {
      fontSize: "18px",
      color: "#f1c40f",
      fontStyle: "bold",
      stroke: "#000000",
      strokeThickness: 3,
    });
    text.setOrigin(0.5);
    this.tweens.add({
      targets: text,
      y: y - 40,
      alpha: 0,
      duration: 800,
      ease: "Cubic.easeOut",
      onComplete: () => text.destroy(),
    });
  }

  private spawnComboPopup(x: number, y: number, depth: number): void {
    const text = this.add.text(x, y - 26, `Combo x${depth}!`, {
      fontSize: "22px",
      color: "#ff9800",
      fontStyle: "bold",
      stroke: "#000000",
      strokeThickness: 4,
    });
    text.setOrigin(0.5);
    text.setScale(0.6);
    this.tweens.add({
      targets: text,
      y: y - 90,
      scale: 1.2,
      alpha: 0,
      duration: 1100,
      ease: "Cubic.easeOut",
      onComplete: () => text.destroy(),
    });
  }

  showLevelCleared(level: number): void {
    this.onLevel(level + 1); // the server has already advanced — keep UI in sync
    this.onLevelCleared(level);
    this.sfx.playLevelUp();

    const cx = (FIELD_SIZE * CELL_SIZE) / 2;
    const cy = (FIELD_SIZE * CELL_SIZE) / 2;

    // Confetti first so the banner arrives in front of it.
    this.emitConfetti(cx, cy);

    const banner = this.add.text(cx, cy, `Level ${level} Clear!`, {
      fontSize: "32px",
      color: "#f1c40f",
      fontStyle: "bold",
    });
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

  /**
   * Level-clear confetti: one emitter per palette colour so particles carry
   * distinct tints (Phaser's tint is emitter-scoped, not per-particle).
   * ~60 particles total, gravity-affected, 1.5-second fade.
   */
  private emitConfetti(x: number, y: number): void {
    const lifespan = 1500;
    for (const colour of BRICK_COLORS) {
      const emitter = this.add.particles(x, y, "particle", {
        speed: { min: 150, max: 360 },
        angle: { min: 0, max: 360 },
        scale: { start: 0.9, end: 0.1 },
        alpha: { start: 1, end: 0 },
        rotate: { min: 0, max: 360 },
        lifespan: { min: lifespan * 0.6, max: lifespan },
        quantity: 0,
        tint: colour,
        gravityY: 220,
      });
      emitter.explode(6);
      this.time.delayedCall(lifespan + 100, () => emitter.destroy());
    }
  }

  private emitMatchBurst(x: number, y: number, colour: number): void {
    // 16 particles tinted to the brick colour, flying outward with a touch of
    // gravity so they arc downward as they fade. Scale shrinks over lifespan
    // and alpha fades — gives a "shatter + sparkle" read rather than the
    // flat "six dots sliding apart" we had before.
    const lifespan = 500;
    const emitter = this.add.particles(x, y, "particle", {
      speed: { min: 80, max: 220 },
      angle: { min: 0, max: 360 },
      scale: { start: 0.9, end: 0 },
      alpha: { start: 1, end: 0 },
      rotate: { min: 0, max: 360 },
      lifespan,
      quantity: 0,
      tint: colour,
      gravityY: 260,
    });
    emitter.explode(16);
    this.time.delayedCall(lifespan + 100, () => emitter.destroy());
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
