# BrickShooter — Design Document

This is the game's specification. It is deliberately implementation-adjacent
but framework-neutral: everything here is enforced by pure Python under
`v2/domain/` (no Kivy, no FastAPI, no Phaser) and should hold for any
future port.

## 1. Core architecture

The game is structured as **ports and adapters** (clean architecture). The
domain knows only rules and events; every UI, transport, and renderer is a
swappable adapter.

```
          DOMAIN            (v2/domain/, pure Python)
            Entities: Brick, CellIntention, Field
            Rules:    shot, movement, crosser, matching, refill, history
            Facade:   Game — owns field + score + level + history + chain_depth

            emits DomainEvent:
              BrickShot, BrickMoved, BrickMatched, BrickCrossed,
              LaunchZoneRefilled, ScoreChanged, LevelCleared,
              StateReverted, GameOver

         ▲                                        │
         │ GameInputPort                          │ GamePresenterPort
         │ (shoot / undo / new_game)              │ (on_event)
         ▼                                        ▼

       ADAPTER(S)            INPUT              OUTPUT
         - WS bridge (backend/adapters/):
             JSON frame ↔ GameInputPort
             DomainEvent → JSON frame
         - Phaser scene (frontend/src/):
             pointerdown on a launcher cell → shoot message
             DomainEvent → tween / particle / sound
```

Each use case returns an ordered list of events. Adapters fan those events
out to their presenter. The domain has no knowledge of real time — the
resolution cycle runs to completion in one synchronous pass; animations and
audio are staged by the adapter based on the event sequence.

---

## 2. Game mechanics and rules

> This chapter is normative. If code and document disagree the code wins,
> but every claim here has been cross-checked against `v2/domain/`.

### 2.1 Board geometry

- The board is a fixed **16 × 16** cell grid (`FIELD_SIZE = 16`).
- Coordinates are `(row, col)` with `(0, 0)` at the top-left. Row grows
  downward, column grows rightward.
- The **play area** is the inner **10 × 10** square spanning rows and
  columns `3 .. 12` inclusive (`PLAY_AREA_START = 3`,
  `PLAY_AREA_END = 13` — a Python-style exclusive upper bound).
- The **launcher zone** is the 3-cell-deep border around the play area
  (`LAUNCH_ZONE_DEPTH = 3`). Concretely it covers, for each play row,
  columns `0..2` (left) and `13..15` (right), and for each play column,
  rows `0..2` (top) and `13..15` (bottom).
- The four **corners** (rows 0–2 × cols 0–2, and the three mirrored 3×3
  blocks) never hold gameplay bricks — they are only used by the UI for
  controls.

### 2.2 Cells and bricks

Every cell of the 16×16 grid holds a `Brick` with two fields:

- `intention: CellIntention`
  - `VOID = 0` — empty cell.
  - `TO_LEFT = 1`, `TO_RIGHT = 2`, `TO_UP = 3`, `TO_DOWN = 4` —
    brick is moving in that cardinal direction; one cell per movement
    tick while its target cell is VOID.
  - `STAND = 5` — brick is stationary; neither moves of its own accord
    nor blocks with any "gravity." Purely an obstacle.
- `color_index: int | None` — index into a palette of 10 colours
  (`COLOR_NAMES` in `domain/constants.py`). Colour is only meaningful for
  non-VOID bricks. Difficulty limits which colour indices the game
  actually uses (see 2.8).

"Ammunition" is nothing more than STAND bricks placed in the launcher
zone; when you fire, one of them has its intention flipped to the
corresponding directional value. A brick's colour is never re-assigned
during play — it flies with the colour it had in the launcher.

### 2.3 Launcher queues

There are **40 queues**: one per play-area row on the left side, one per
row on the right, one per play-area column on the top, one per column on
the bottom. Each queue is 3 cells deep, ordered **innermost → outermost**
(innermost = the cell adjacent to the play area).

Concretely, for play-area row `r`:

- Left queue:  `(r, 2), (r, 1), (r, 0)`  (innermost first)
- Right queue: `(r, 13), (r, 14), (r, 15)`

Analogously for columns. Across all 40 queues every launcher-zone cell is
owned by exactly one queue.

### 2.4 Starting / preparing a board

`Game.new_game()` resets `level = 1`, `score = 0`, clears history, then
calls `_setup_board()`:

1. All launcher cells (in all 40 queues) are populated with STAND bricks
   whose colours come from the injected `pick_color()` callable
   (defaulting to `random.randint(0, num_colors - 1)`).
2. `num_obstacles` STAND bricks are placed at random VOID cells inside
   the play area, with colours drawn the same way.
   - Default `num_obstacles = level + 1`, so level 1 opens with 2
     obstacles, level 2 with 3, etc.
   - Placement rejects cells that already hold a brick and retries, so
     you always end up with exactly `num_obstacles` bricks regardless of
     collisions.

Because the play area starts with obstacles (not just launchers), the
very first shot always has a legal target in at least one row or column.

### 2.5 Shooting

A shot is triggered by tapping one of the **4 launcher strips** — the
cells just outside the play area, adjacent to its edges:

- Left strip:  col = 2, any play row.
- Right strip: col = 13, any play row.
- Top strip:   row = 2, any play col.
- Bottom strip: row = 13, any play col.

These are the only 40 cells that can produce a shot. The other two
columns/rows of each launcher zone hold ammo but are not tappable.

The shot fires if **all three preconditions** hold (see
`domain/rules/shot.py`):

1. **Target cell is VOID.** The play-area cell immediately inside the
   tapped strip must be empty:
   - Left tap (r, 2)  → target (r, 3)
   - Right tap (r, 13) → target (r, 12)
   - Top tap (2, c)   → target (3, c)
   - Bottom tap (13, c) → target (12, c)
2. **An obstacle exists somewhere along the shot's path**, i.e., at
   least one of the remaining interior play-area cells in that row
   (for horizontal shots) or column (for vertical shots) is non-VOID.
   You cannot shoot into an empty line.
3. **At least one launcher cell in that queue holds a brick.** The game
   picks the **innermost** populated cell in the queue as the ammo.

When all three hold, the ammo brick's `intention` is changed from STAND
to the directional value pointing into the play area:

| Tap strip | Direction assigned |
|---|---|
| Left   | `TO_RIGHT` |
| Right  | `TO_LEFT`  |
| Top    | `TO_DOWN`  |
| Bottom | `TO_UP`    |

A single `BrickShot(launcher_cell, ammo_cell, direction)` event is
emitted. **The brick keeps its colour** — only intention changes.

Invalid taps (wrong cell, closed target, empty row/col, no ammo) are
silently ignored — no event.

### 2.6 Resolution cycle

After a successful shot, `Game.shoot()` runs `_resolve()` synchronously
to drive the board to a stable state. The cycle is a double loop.

**Outer loop**, per iteration:
1. **Drain movement** — call the inner loop below until it produces no
   events.
2. **Match pass** — run matching once (see 2.6.2). If it cleared any
   groups, emit events and restart from step 1. Bricks that had lost
   their mover may now be free to move; matching can unblock further
   motion.
3. **Refill pass** — run refill once (see 2.6.3). If any launcher was
   refilled, emit events and restart from step 1. Refills can push
   bricks into positions that complete new matches or enable movement.
4. **Termination** — if the outer iteration produced no movement, no
   match, and no refill, the cycle is stable and the loop breaks.

**Inner movement loop** (`_drain_movement`): keeps running until both
the movement step and the crosser step return no events for the same
pass. Per pass:

1. **Movement step** (`movement_resolution_step`):
   - Scan every cell in the grid.
   - A brick with a directional intention attempts to move exactly one
     cell in that direction.
   - The move is rejected if any of:
     - The target cell lies outside the board.
     - The brick is **inside the play area** and the target is
       **outside the play area** — that transition is handled by the
       crosser rule, not by movement.
     - The target cell's intention is anything other than VOID.
   - If two bricks want the same VOID cell in the same pass, the first
     one visited in row-major scan order wins; the other is simply not
     moved this pass.
   - Effect: the two cells (source and target) are swapped, so the
     source becomes VOID and the brick retains its intention.
2. **Crosser step** (`handle_board_crossers`):
   - Scan the **inside edge** of the play area (only the four rows/cols
     immediately inside the boundary):
     - Row 3  + `TO_UP`     → crosses into the top launcher
     - Row 12 + `TO_DOWN`   → crosses into the bottom launcher
     - Col 3  + `TO_LEFT`   → crosses into the left launcher
     - Col 12 + `TO_RIGHT`  → crosses into the right launcher
   - For each qualifying brick:
     - The destination is the launcher queue directly outside that edge
       cell, ordered innermost → outermost (3 cells).
     - Existing bricks in that queue shift outward by one cell; the
       **outermost brick is overwritten and lost**.
     - The crosser lands in the innermost queue cell with
       `intention = STAND` and its original colour.
     - The source cell is cleared to VOID.
   - Events emitted per cross: one `BrickMoved` per populated cell that
     shifted (outer-to-inner order so the outermost's discard is
     "overwritten-in-place" rather than a separate destruction event),
     then one `BrickCrossed(from_cell, to_cell=innermost, color_index)`
     at the end.

#### 2.6.2 Match pass (`find_and_remove_groups`)

- Considers only the play area (10 × 10 interior).
- Uses **BFS on 4-adjacent same-colour neighbours** — a match is any
  connected component, not only a straight line. An L-shape or T-shape
  of same-colour bricks is one group.
- Any component with size ≥ `min_group_size` (default **3**) is removed:
  its cells become VOID.
- Base score per removed group (before any chain multiplier):
  `group_size * BASE_SCORE * ((group_size - min_group_size) + 1)`
  with `BASE_SCORE = 10`. For the default minimum of 3:

  | Group size | Base score |
  |---|---|
  | 3 | 30 |
  | 4 | 80 |
  | 5 | 150 |
  | 6 | 240 |
  | 7 | 350 |

- **Chain multiplier.** The resolution cycle tracks a `chain_depth`
  counter that starts at 0 at the top of every `shoot()` and is
  incremented on every match pass that scores at least one group.
  The `ScoreChanged.delta` actually added to `score` is:

  ```
  delta = sum_of_group_scores_this_pass * chain_depth
  ```

  So the first match batch in a shot scores ×1 (unchanged), a second
  batch in the same cycle (triggered by refills or unblocked movement)
  scores ×2, a third ×3, and so on. The client's "Combo ×N" popup is
  a direct visualisation of that multiplier — it's a real bonus, not a
  cosmetic.

- Emits one `BrickMatched(cells, color_index)` event per group cleared.
  The outer cycle emits one `ScoreChanged(delta, total)` after the
  whole match pass; `delta` already includes the multiplier.

#### 2.6.3 Refill pass (`refill_launch_zones`)

- Iterates over all 40 launcher queues (innermost → outermost per queue).
- For each queue, on the **first VOID encountered**:
  - Shift every cell from that index outward one step inward — i.e. the
    VOID propagates outward.
  - Place a fresh STAND brick at the outermost cell with a new
    `pick_color()` result.
  - Emit one `BrickMoved` per populated shifted cell, then one
    `LaunchZoneRefilled(new_cell, color_index)` for the new outermost
    brick.
  - Move on to the next queue (at most one refill per queue per pass;
    multiple voids in a queue are filled across successive passes as
    the outer cycle re-enters).

### 2.7 Level progression and game over

After the resolution cycle finishes, `_check_level_or_game_over()` runs:

1. **Level clear** — if every cell in the play area is VOID:
   - Emit `LevelCleared(level=old_level)`.
   - Increment `level`.
   - Clear the undo history (undo cannot cross a level transition).
   - Re-run `_setup_board()` with the new `num_obstacles = level + 1`.
   - The session continues; score is **not** reset.
2. **Game over** — if the play area is non-empty but **no shot is
   possible from any of the 40 launcher strips** (i.e. every candidate
   tap fails at least one precondition from 2.5):
   - Emit `GameOver(reason="No more moves.", won=False, level, score)`.
   - The session is over. A scoreboard entry is recorded server-side.
3. Otherwise nothing is emitted and the player acts again.

There is no "won=True" game over: clearing the board always becomes a
level-up, never a session end.

### 2.8 Difficulty

Chosen per-session in the client UI; passed in the `new_game` message.
Preset effect is only on the palette size:

| Preset  | `num_colors` |
|---|---|
| Easy    | 5 |
| Normal  | 7 |
| Hard    | 9 |

Fewer colours means matches form more readily, so easy rounds drain the
board faster. Obstacle count scales with level, independent of
difficulty.

### 2.9 Undo

- Before every shot the facade snapshots `(deepcopy(field), score)` onto
  an in-memory stack.
- If the shot rule rejects the tap, the speculative snapshot is popped
  back off and no history entry is kept.
- `Game.undo()` pops the top snapshot, restores field + score, and
  emits `StateReverted(score)`.
- History is cleared on `new_game()` and on every level transition —
  you cannot undo past the start of the current level.
- There is no limit on depth beyond memory.

---

## 3. Use cases and the event stream

### 3.1 "Player shoots a brick"

Trigger: tap on a launcher strip cell (2.5).

Event sequence for a successful shot (typical example: horizontal shot
that clears a triplet):

```
BrickShot(launcher_cell, ammo_cell, direction)
BrickMoved(ammo_cell → ammo_cell + step)        ← one per cell travelled
BrickMoved(...)
...                                             ← repeats while path open
BrickMatched(cells, color_index)                ← (if the shot completes a match)
ScoreChanged(delta, total)
BrickMoved(...)                                 ← movement on cells freed by the match
...
LaunchZoneRefilled(new_cell, color_index)       ← one per queue that needed refilling
...
(possibly) BrickMatched/ScoreChanged again      ← if a refill caused a chain
...
LevelCleared(level) | GameOver(reason, won, level, score)  ← at most one, only at cycle end
```

All events emitted by one `shoot()` call arrive in this order, as a
single ordered list.

### 3.2 "Player undoes a shot"

Trigger: client sends `{"type": "undo"}`.

Event sequence:

```
StateReverted(score)    ← only if history was non-empty; no events otherwise
```

The client repaints the whole field from a snapshot the server sends
after `StateReverted` — rebuilding exact state from the reverse of each
event would be fragile given refill randomness.

### 3.3 "Player starts a new game"

Trigger: `{"type": "new_game"[, "difficulty": "easy"|"normal"|"hard"]}`.

The domain `new_game()` returns no events. The backend handler follows
with a `snapshot` frame describing the fresh board.

---

## 4. Implementation contract

### 4.1 Ports

- **`GameInputPort`** (typing.Protocol, runtime-checkable):
  - `new_game() -> list[DomainEvent]`
  - `shoot(cell: tuple[int, int]) -> list[DomainEvent]`
  - `undo() -> list[DomainEvent]`
- **`GamePresenterPort`** (typing.Protocol, runtime-checkable):
  - `on_event(event: DomainEvent) -> None`

### 4.2 `DomainEvent` variants

All are frozen `@dataclass`es, immutable, hashable, compared by value.
A test in `v2/tests/test_codec.py` pins the JSON wire shape for each.

| Event | Payload |
|---|---|
| `BrickShot` | `launcher_cell`, `ammo_cell`, `direction` (enum name string) |
| `BrickMoved` | `from_cell`, `to_cell` |
| `BrickMatched` | `cells` (tuple), `color_index` |
| `BrickCrossed` | `from_cell`, `to_cell`, `color_index` |
| `LaunchZoneRefilled` | `new_cell`, `color_index` |
| `ScoreChanged` | `delta`, `total` |
| `LevelCleared` | `level` (the level just cleared) |
| `StateReverted` | `score` (score restored to) |
| `GameOver` | `reason`, `won`, `level`, `score` |

### 4.3 Determinism

The only non-deterministic inputs are `pick_color()` (called at brick
spawn / refill) and `rng.randint(...)` (called for obstacle placement in
`_setup_board`). Both are injectable via the `Game` constructor so tests
can produce deterministic event streams. In production both default to
the global `random` module.

### 4.4 Invariants (at the end of every `shoot()` / `undo()` / `new_game()`)

- Every non-VOID brick has a non-None `color_index`.
- Every non-VOID brick on a launcher cell has `intention = STAND`. The
  shot rule flips one ammo brick to a directional intention, but the
  first pass of `_drain_movement()` always moves it into the play area
  before `_resolve()` returns (the shot-rule precondition requires the
  target edge cell to be VOID, so the move is never blocked on that
  pass).
- The four inside-edge cells of the play area never carry an outward
  intention at rest — the crosser rule always processes them in the
  same drain pass that produces them.
- If the play area has at least one non-VOID cell and `_any_shot_possible`
  is false, a `GameOver` event was emitted in the last action — no
  further `shoot()` calls can succeed until `new_game()`.
