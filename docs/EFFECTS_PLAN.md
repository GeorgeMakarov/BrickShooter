# Visual Effects — Follow-on Plan

The v2.0.0 release nails mechanics and deploy. The animations are functional
but minimal — six hand-drawn rectangles for the match "burst," a plain white
rectangle for shot flash, no motion trail, no screen-level feedback. This
plan stages the upgrades so each chunk is visible on its own and can be
reviewed before moving to the next.

Target stack stays: **Phaser 4** on TypeScript. No engine swap. Everything
here builds on `GridScene` and the `SceneEffects` port the domain already
drives.

## Working principles

- **Juice first, shaders later.** Particles, shakes, and tweens are cheap
  and obvious; filters/shaders come last.
- **Effects are one-liner opt-ins.** Each effect reads the same event stream
  that's already in production — no new backend messages, no protocol
  changes. Everything lives in `v2/frontend/src/scenes/`.
- **Keep tests green on every phase.** Unit tests cover pure logic
  (`event_dispatch`, `grid_render`). The effects themselves are visual and
  tuned by eye; they don't need unit tests but must not break the existing
  ones or the typecheck.
- **Deploy after each phase** only if the user likes what they see in local
  dev.

## Phases

### Phase 1 — "Juice" (matches feel like they mean something)

| # | Effect | Trigger | Rough implementation | LOC |
|---|---|---|---|---|
| 1.1 | Real particle emitters on match | `BrickMatched` | Swap my six `Rectangle` sprites for `scene.add.particles()` with colour tint matching the cleared brick, 12–20 particles per brick, spread lifetime, gravity. | ~30 |
| 1.2 | Shot-flash upgrade | `BrickShot` | Replace the current 32×32 white rectangle with a radial glow (large Circle tweening scale up + alpha down) plus 4–6 sparkle particles. | ~20 |
| 1.3 | Screen shake on big matches | `BrickMatched` with `cells.length ≥ 5` | `this.cameras.main.shake(duration, intensity)` proportional to group size, clamped. | ~10 |

**Exit criterion:** a triplet match throws a coloured puff; a 5+ match shakes
the whole board for 150 ms; firing a shot visibly "pulses" at the launcher.

### Phase 2 — Motion (the flight of a brick)

| # | Effect | Trigger | Rough implementation | LOC |
|---|---|---|---|---|
| 2.1 | Motion trail on in-flight bricks | `BrickMoved` for a brick with directional intention | Spawn a faded, smaller sprite clone each tween frame; destroy on a short timer. Or use `PostFX` motion blur (heavier). | ~40 |
| 2.2 | Level-clear flourish | `LevelCleared` | Confetti burst from the board centre: ~60 coloured particles, outward spread, 2 s fade. Current text banner stays. | ~30 |

**Exit criterion:** watching a ball fly across the board leaves a visible
streak; clearing a level pops confetti for ~2 s before the next level sets up.

### Phase 3 — Combo feedback (rewards for chains)

| # | Effect | Trigger | Rough implementation | LOC |
|---|---|---|---|---|
| 3.1 | Score popup at match site | `ScoreChanged` with preceding `BrickMatched` | Small yellow text (`+30`) tweened up-and-fade at the match centroid. Track the last BrickMatched's centroid in the dispatcher. | ~30 |
| 3.2 | Chain counter | A `BrickMatched` follows another in the same resolution cycle without a user shot in between | Count matches per cycle; on second+ match, show "x2", "x3" in the corner; reset on next `BrickShot`. | ~40 |

**Exit criterion:** the second match triggered by the same shot pops a "Combo
x2" indicator that survives until the next shot.

### Phase 4 — Audio (not visual, but same "juice" dimension)

| # | Effect | Trigger | Rough implementation | LOC |
|---|---|---|---|---|
| 4.1 | Shot click | `BrickShot` | Short synth click via `scene.sound.add('click').play()`. Sound files ship with the frontend bundle. | ~15 |
| 4.2 | Match pop | `BrickMatched` | Pitch-shifted pop proportional to group size. | ~15 |
| 4.3 | Level-up chime | `LevelCleared` | Two-note ascending synth. | ~10 |

**Exit criterion:** a mute toggle in the corner controls lets users silence
everything; default ON.

### Phase 5 — Polish (optional, if it still looks flat)

| # | Effect | Trigger | Rough implementation | LOC |
|---|---|---|---|---|
| 5.1 | Bloom on active sprites | in-flight bricks | Phaser FX pipeline `addGlow` on the moving sprite. | ~15 |
| 5.2 | Idle board pulse | no input for >10 s | Gentle breathe animation on the nearest launcher to hint at what the user can do. | ~25 |
| 5.3 | PWA manifest + offline shell | page load | `manifest.webmanifest` + a minimal service worker so dad can add an icon to his home screen and play even briefly offline. | ~50 + asset work |

## Deploy cadence

After each phase:

```
cd v2/frontend && npm run build
pscp -i ~/.ssh/your-key.ppk -r v2/frontend/dist/* root@<YOUR-SERVER>:/opt/brickshooter/frontend/
```

No backend changes in phases 1–4 (events already carry everything needed).
Phase 5.3 (PWA) touches frontend only too.

## Decisions open

1. **Sound assets** (Phase 4): self-recorded, CC0 library, or synth via
   `tone.js`? Synth is smaller and programmable — probably the right fit.
2. **Chain counter location** (Phase 3.2): corner-tr next to score? Float
   on the board? Tradeoff: corner is discoverable but static; floating is
   more "game-feel" but potentially in the way.
3. **Confetti palette** (Phase 2.2): use the 10-colour brick palette
   (coherent) or classic confetti (party vibes)?
