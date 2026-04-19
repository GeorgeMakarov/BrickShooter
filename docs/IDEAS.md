# BrickShooter — Ideas & Rough Plans

A loose brainstorm, not a spec. Goals:

- **Make it harder for experienced players** (your dad's complaint — he
  cleared level 1 too fast).
- **Give larger matches a real payoff** so "just shooting any triplet"
  stops being optimal and planning a 4- or 5-match becomes attractive.
- **Add variety** without breaking v1/v2 parity of the core rules.

Each idea is rated for **impl cost** (frontend only / backend only /
both) and for **design risk** (does this change the fundamental feel?
might it make the game worse?). Nothing here is committed — this file
is the palette we pick from.

## 1. Special bricks (your ask + extensions)

All of these are new `CellIntention` / metadata on a brick that the
domain already stores as `Brick(intention, color_index)`. Extending the
brick to carry a `kind` field (ordinary / bomb / wildcard / …) or
reusing a dedicated colour index (10 is already used — we'd add more)
is the cheapest path.

### 1.1 Bomb brick — reward for clearing a 4-group

**Your preferred shape** (discussable):

| | |
|---|---|
| **Trigger** | A group of exactly 4 same-colour bricks clears. |
| **Effect** | A **random brick in one of the launcher queues** is converted into a bomb brick — visually distinct (bomb icon overlaid on the coloured body), but functionally still ammunition. The player fires it later like any brick. |
| **On firing** | The bomb flies like a normal brick. When it **comes to rest** (lands in the play area, or crosses to the opposite launcher), it detonates: clears its own cell + the 3×3 neighbourhood (or + cross), regardless of colour. |
| **Matching** | A bomb brick still carries a colour so it can participate in a normal match during flight; if it matches as part of a triplet+, it detonates *in addition to* the regular match score — double bonus. |
| **Score** | Base 4-match: 80. Detonation: flat +100 (or: 10 × cells_cleared by the blast). |
| **Impl cost** | Backend: add `kind` field on `Brick`, convert-random-launcher-brick on 4-match, detonation rule when a bomb settles or matches, new `BrickExploded` event carrying cleared cells. Frontend: bomb sprite variant, explosion animation (reuse match-burst particles, bigger radius, screen shake proportional to clear size). |
| **Design risk** | Low-medium. Delayed-reward shape matches puzzle genre convention ("weapon in inventory, choose when to use"). Random launcher selection introduces a small luck element — some players won't see the bomb in their immediate shot choices. |

**Alternative (my original sketch, kept for comparison)**:
The completer of the 4-group stays in the play area as a bomb brick,
detonates on next match involvement. Pros: no luck (bomb is exactly
where the player placed it), no extra ammo selection. Cons: occupies a
play-area cell as an obstacle until triggered, which may feel
counter-productive when the player is trying to *clear* the play area.

Open variant questions either way:
- 3×3 area vs. + cross? 3×3 is bigger payoff; + cross is more
  surgical (and easier to telegraph in the UI).
- Should the bomb trigger chain detonations if its blast includes
  another bomb? Fun — but needs careful balance.
- For "your" version: is the lucky launcher queue visible to the
  player before they fire? (Yes — the bomb icon is visible on the
  brick.)

### 1.2 Wildcard brick — reward for clearing a 5-group

**Your preferred shape** (mirroring 1.1):

| | |
|---|---|
| **Trigger** | A group of 5+ same-colour bricks clears. |
| **Effect** | A **random brick in one of the launcher queues** is converted into a wildcard — visually a rainbow tile or a white star overlay, still occupies its queue cell as ammunition. |
| **On firing** | The wildcard flies like any brick. When it **comes to rest** (lands or crosses), it joins its BFS group: if any of its 4-adjacent play-area neighbours carry a colour and form (together with the wildcard itself) a connected component of 3+ cells, the group clears — the wildcard counting as that colour for matching purposes. |
| **Ambiguity resolution** | If the wildcard is adjacent to two different-coloured neighbours and both could form a group: pick the **larger** resulting group. Tie-breaker: pick the colour of the cell visited first in row-major scan order. |
| **Score** | Base 5-match: 150 (for the triggering match). When the wildcard is later consumed in a match, a **+50% bonus** on that match's score (rounded up). |
| **Impl cost** | Backend: `BrickKind` field (shared with 1.1), matching rule extended so a wildcard joins a same-colour component via BFS regardless of colour, new `BrickWildcardActivated` event. Frontend: sprite variant (rainbow or iridescent overlay). |
| **Design risk** | Low. Standard in puzzle games (Bejeweled's "star gem," Candy Crush's colour bomb). |

Open variant questions:
- If the wildcard lands **without** any adjacent same-colour pair, does
  it just sit there as ordinary ammo (colourless, unmatchable) until
  the board shifts? Or does it auto-detonate something small? Sitting
  quietly is simpler.
- Two wildcards adjacent on landing → should they trigger a
  "super-clear" (entire row/col, or all of one colour)? Same spirit as
  section 1.3's 6-group colour-bomb tier — might fold the idea in
  there rather than double-tiering here.

### 1.3 Extension ideas (if bombs + wildcards land well)

**Geometric ceiling.** Before any shot, no same-colour component in the
play area is larger than 2 (anything ≥ 3 was cleared last cycle). A
single shot brings in 1 cell and can merge at most 3 adjacent 2-clusters
(the fourth side of the landing cell is always the VOID trail the shot
came from). So **the theoretical maximum group on a single shot is
1 + 3 × 2 = 7**. 8- or 9-groups are not achievable under the current
rules.

| Tier | Group size | Reward idea |
|---|---|---|
| Small | 3 | Normal score, no extra (the baseline). |
| Bomb | 4 | Ammunition-zone bomb (see 1.1). |
| Wildcard | 5 | Ammunition-zone wildcard (see 1.2). |
| Colour-bomb | 6 | Ammunition-zone brick that, on landing, clears every brick of the *colour it touches first* anywhere on the play area — fewer, larger strategic plays. |
| Row/Col blaster | 7 | Ammunition-zone brick that, on landing, clears its entire row and column of the play area. Achievable only by threading three 2-clusters, so feels genuinely earned. |

L-shape / T-shape match specialisations are dropped — in the current
BFS rule a 4-brick L-match and a 4-brick line-match are
indistinguishable to the domain (both are a size-4 component). Not
worth inventing a distinction the rules don't make.

## 2. Difficulty knobs for the core game

The simplest ways to make "level 5" actually feel like level 5:

### 2.1 Steeper obstacle curve

Today: `num_obstacles = level + 1` (level 1 → 2 obstacles, level 10 →
11). Dad finds early levels trivial.

Alternatives:
- `level * 2` (level 1 → 2, level 5 → 10, level 10 → 20). Much steeper,
  board gets crowded fast.
- `level + difficulty_bonus` where difficulty_bonus is `0/2/4` for
  easy/normal/hard, so hard starts at 5 obstacles at level 1.
- `min(level + 1, 20)` with a cap to avoid an unclearable board.

**Recommended**: make the formula per-difficulty:

| Difficulty | Obstacles at level L |
|---|---|
| Easy | `L + 1` (current) |
| Normal | `L + 2` |
| Hard | `2L + 1` |

Impl cost: backend only, one-line change in `Game.num_obstacles`. Low
risk.

### 2.2 Indestructible ("stone") bricks

A subset of obstacles that cannot be matched **and cannot be moved** —
permanent walls for the level. Turns each level into a genuine puzzle
where the board shape itself is the challenge.

The current collision model makes "pushable stone" incoherent: a shot
either stops when it hits a brick (nothing moves) or crosses through an
empty lane (nothing is pushed). Inventing a push-on-impact rule just for
stones would require a Sokoban-style chain-push mechanic, which is a
much bigger rule change than this idea is meant to be. So stones commit
to being truly immovable.

| | |
|---|---|
| **Representation** | `BrickKind.STONE`, ignored by matching, movement, and crosser rules. A shot that hits a stone stops adjacent to it exactly like hitting any other brick. |
| **Visual** | Greyscale block, distinct from any palette colour, with a masonry/cracked texture so it reads as "permanent" at a glance. |
| **Placement** | 1–2 per level at high difficulty, scattered in the play area at level setup. |
| **Clear condition** | Level ends when the play area has **no non-stone bricks**. Stones persist until the session ends. |
| **Removal (optional)** | If bombs / row-column blasters ship (idea 1.1, 1.3), their effect destroys stones in their blast radius — that's the only counterplay. Without those, stones are pure obstacles and the player has to route around them. |
| **Impl cost** | Backend: `BrickKind`, matching/movement/crosser skip stones, level-clear rule checks only non-stone cells. Frontend: sprite variant. |
| **Risk** | Medium. Changes "clear the board" victory condition. Only meaningfully fun once 1.1/1.3 exist — before then, stones are deadweight. Worth gating this idea behind the bomb-brick sprint. |

### 2.3 Durable bricks (HP ×N)

Same idea, less extreme: a brick that is matchable by colour, but
survives N matches before clearing. Players see a counter on its face
(×3, ×2, ×1) ticking down with every hit.

| | |
|---|---|
| **Representation** | `Brick.hp: int` field defaulting to 1. Durable bricks start with hp ∈ {2, 3} (possibly higher at very high levels). |
| **Match interaction** | Durable bricks participate in BFS normally via their `color_index`. When a match would clear them, instead `hp -= 1`. If `hp == 0`, the cell clears as normal (VOID). If `hp > 0`, the brick stays in place and a `BrickDamaged(cell, remaining_hp)` event is emitted. |
| **Same-match multiple damage** | A single match always deals exactly 1 damage to each durable brick in its component — not per triplet, not per chain level. Simpler to reason about. |
| **Score** | Every hit on a durable brick counts it toward the match's group size (so a 3-group including an HP-3 brick scores 30 each time, for three matches to clear it). |
| **Movement** | Durable bricks in the play area still carry STAND intention and can be pushed by the crosser/refill mechanics exactly like normal bricks. HP is preserved through moves. |
| **Bomb interaction (if 1.1 ships)** | A bomb's 3×3 detonation deals 1 damage per durable brick it touches, same as a match. HP-3 brick in a bomb radius: bomb takes it to HP-2, doesn't destroy it outright. Keeps the mechanic tough. |
| **Visual** | Numeric badge on the face: ×3, ×2, ×1. Numbers fade as HP drops; brightest at full health. Small crack overlay after each hit for texture. |
| **Placement** | As part of the "obstacle" count at higher difficulty — e.g. on `Hard` from level 3 onward, half the obstacles are HP-2 durable, above level 6 some HP-3. |
| **Impl cost** | Backend: `hp` field on Brick, matching rule adjusts clearance, new event type, snapshot encodes hp. Frontend: numeric overlay + crack sprite + particle tint for damage-vs-clear distinction. |
| **Risk** | Low. Well-understood mechanic from other match-3 games; doesn't change the victory condition (level still clears when play area is fully VOID). |

Open design questions for 2.3:

- Does HP decrement mean the brick **still shows the match's particles**
  (just doesn't vanish)? I'd say yes — visual feedback is important
  when you land a match and the target "survives."
- Does the player get a small score bonus *when* a durable finally
  clears, or just the normal match score on the clearing hit? Probably
  no bonus — keeping the reward proportional to the work.
- Can a durable brick ever spawn as a **launcher brick** (ammo)? I'd
  say no — HP is a play-area concept; the launcher should stay
  predictable.

### 2.4 Move limit / shot budget

Per level, a finite number of shots. Out of shots → game over.
Encourages planning.

| | |
|---|---|
| **Formula** | `base_shots + level * 5` (level 1: 10 shots; level 10: 55). |
| **UI** | Shot counter in the top-right corner replacing or alongside Level. |
| **Impl cost** | Backend: shot counter + new `ShotsChanged` event + game-over on zero. Frontend: corner widget. |
| **Risk** | High — fundamentally changes game feel. Worth a "Campaign" mode rather than default. |

### 2.5 Timer per shot

N seconds to fire each shot — run out, game over (or forfeit the shot).
Makes the game twitchy. Probably a bad fit for dad. Listed for
completeness; I'd skip unless you want a "Blitz" mode.

### 2.6 Shrinking launcher queues

Start with 3-cell queues, at higher levels launchers are 2-cell then
1-cell. Ammo runs out faster, forcing more careful shots.

### 2.7 Colour rotation

Every N levels, the available palette rotates — the bricks you see
change. Prevents pattern memorisation.

## 3. Game modes (variety)

These are new entry points on the main screen, not rule changes.

### 3.1 Campaign

Fixed hand-crafted levels with goals — "clear in ≤15 shots" or "clear
with exactly one bomb detonation." Replaces random obstacles with
author intent.

Impl: backend loads levels from JSON; frontend adds a level-select
screen. ~2–3 days.

### 3.2 Daily challenge

Seeded random board — everyone who plays today sees the same layout.
Global daily leaderboard.

Impl: backend seeds `Game._rng` from a day-stamped value; scoreboard
filters by seed. Small.

### 3.3 Endless (survival)

Current game, but every N shots a new obstacle is injected into a random
play-area cell. Score climbs until the board fills up.

Impl: backend tick (per shot count) inserts a brick via the same
pick_color. Small backend change.

### 3.4 Puzzle / "one-shot wonder"

Pre-set layout, one shot, must clear everything. Think chess puzzles.
Heaviest authoring burden but most replayable per line of code.

## 4. Meta-progression & social

### 4.1 Stats page

Tracks per-player: best score per difficulty, largest chain, biggest
group, total games, bomb detonations, wildcards used. Read from the
server's gameplay logs (already capture everything we need). Adds a
button to the overlay.

Impl: backend aggregation endpoint, frontend modal. Modest.

### 4.2 Scoreboard filters

Currently top-10 per difficulty, flat. Add tabs: All-time / This month /
Today. Trivial backend change (filter by `date`).

### 4.3 Replays

Every session is an ordered event stream — the server already logs it.
"Replay last game" could feed the event log back through the frontend
dispatcher. Real cool, fair amount of UI work.

### 4.4 Avatars / profile

Client picks an emoji or short colour string stored with the name. Each
scoreboard row gets a little avatar. Pure frontend.

## 5. Suggested short-term slate

If I had to pick a "next sprint" for this palette, it would be:

1. **Bomb brick (1.1)** — direct dad ask, immediate depth, clean extension of existing rules.
2. **Wildcard brick (1.2)** — direct dad ask, standard puzzle-game reward.
3. **Steeper obstacle curve (2.1)** — one-line change, instantly harder for dad.
4. **Stats page (4.1)** — uses logs we already have; shows off what the game records.

Holds for later:

- Durable bricks (2.3) — strong candidate for the *second* sprint;
  delivers "more challenge" without changing the victory condition.
- Indestructible stone (2.2) — bigger design risk, wait to see if 1 +
  2.1 + 2.3 are enough depth first.
- Shot budget / timer — whole new mode, not a drop-in.
- Campaign / daily — needs content authoring or cross-session state.

## 6. Brick kind — the design seam for 1.x

Making `Brick` carry a `kind` field is the shared plumbing for every
item in section 1. Proposal:

```python
class BrickKind(IntEnum):
    NORMAL = 0
    BOMB = 1
    WILDCARD = 2
    # future:
    # STONE = 3
    # COLOUR_BOMB = 4
    # ROW_CLEAR = 5
    # COL_CLEAR = 6

@dataclass
class Brick:
    intention: CellIntention = CellIntention.VOID
    color_index: int | None = None
    kind: BrickKind = BrickKind.NORMAL
```

Matching rule extension:
- When BFS visits a brick, `kind == WILDCARD` colour-matches any
  neighbour.
- When a group of size 4+ clears and the colour is consistent, the
  "completer" brick (the last one to join the group) becomes the
  reward kind — BOMB for 4, WILDCARD for 5+, colour bomb for 6+, …

Emitting reward spawns as a new event (`RewardBrickSpawned`) lets the
frontend fire a distinct animation per tier.

Serializing over the wire is a small codec addition; snapshots grow a
`kind` field per cell.

---

All of the above is up for editing — push back on anything that
doesn't feel right for a single-player puzzle, and we'll prune.
