# BrickShooter — Architecture Migration Plan

## 1. Goals

1. **Engine-swappable**: game rules must run independently of any rendering/UI framework. Swapping Kivy → Godot → Phaser should not touch domain code.
2. **Rich visual effects**: smooth tweens, particles on match/blast, motion trails — without hand-rolling each one as in v1.
3. **Browser-playable via a link**: deploy a single URL hosted on user's own server so dad (and anyone else with the link) can play without installing anything. Ideally static files only (no backend runtime).
4. **Preserve v1 logic**: reuse rules already debugged in `model.py` (resolution cycle, crossers, refill, matching, scoring, undo).

## 2. Current state (v1)

- **Stack**: Python 3.10 + Kivy 2.3
- **Pattern**: MVC. `model.py` (pure logic, ~430 LOC), `view.py` (Kivy widgets, ~490 LOC), `controller.py` (wiring, ~160 LOC).
- **Strengths**: model is already near-pure (only uses `random`, `copy`, stdlib enum) — close to a clean domain layer.
- **Weaknesses**:
  - View couples rendering, animation choreography, and widget state tracking. Ghost-trail hack leaks widgets.
  - Controller directly calls view methods (`draw_field`, `animate_events`, `update_score`) — no abstraction.
  - `model.save_state` uses `deepcopy(field)` — fine, but not reified as a domain event stream, so the view can't diff what changed without re-rendering the whole grid.
  - No tests.

## 3. Target architecture: Ports & Adapters (Clean Architecture)

```
┌──────────────────────────────────────────────────────────────┐
│                      DOMAIN (pure logic)                     │
│  Entities: Brick, CellIntention, Field                       │
│  Services: ResolutionEngine, ShotRules, Scoring, HistoryStack│
│  Emits:    DomainEvent (Moved, Matched, Shot, Refilled, ...) │
└───────────────────────────▲──────────────────────────────────┘
                            │ (no framework imports)
┌───────────────────────────┴──────────────────────────────────┐
│                    APPLICATION (use cases)                   │
│  ShootBrick, Undo, NewGame — coordinate domain, emit events  │
└───────▲─────────────────────────────────────▲────────────────┘
        │ GameInputPort                       │ GamePresenterPort
┌───────┴──────────┐                  ┌───────┴───────────────┐
│  INPUT ADAPTER   │                  │  OUTPUT ADAPTER       │
│  (Kivy touch,    │                  │  (Kivy view, Godot    │
│   HTTP POST,     │                  │   scene, Phaser       │
│   WS message)    │                  │   scene, ...)         │
└──────────────────┘                  └───────────────────────┘
```

### Key primitives to introduce

- **`DomainEvent`** (tagged union): `BrickShot`, `BrickMoved(from, to)`, `BrickMatched(cells)`, `BrickCrossed(from, to)`, `LaunchZoneRefilled(cells)`, `ScoreChanged(delta, total)`, `GameOver(reason)`, `StateReverted(snapshot)`.
  - Replaces the current pattern where the view inspects the whole field after every step. Adapters subscribe instead of polling.
- **`GamePresenterPort`** (interface): one `on_event(DomainEvent)` method. Each rendering backend implements it once.
- **`GameInputPort`**: `shoot(cell)`, `undo()`, `new_game()`. Thin — adapters call these.
- **`Snapshot`**: serializable field + score. Used by undo and (crucially) by save/load, network sync, and the web deployment.

### Why this helps the effects problem

With event streams, the presenter layer knows exactly what happened and *for how long* it's animating. Motion trails, particle bursts on match, score popups — all become "on event X, play effect Y for duration Z." No more ghost-spawner leaks; the engine's native animation system tracks lifetime.

## 4. Deployment options for the browser

Three honest paths, each changes the rest of the plan:

### Option A — Python domain, web via server
- Domain stays Python. Server: FastAPI + WebSocket. Browser: lightweight TS/JS frontend (canvas or PixiJS) that sends `shoot`/`undo` and renders events.
- **Deploy**: Python service + static HTML on your server (needs a persistent process; e.g. systemd + nginx).
- **Pros**: reuses v1 code; Python testable end-to-end.
- **Cons**: two UIs to maintain (Kivy + web); latency visible on slow connections; server cost / uptime.
- **Dad link**: `https://yourserver/brickshooter` — works, but server must be up.

### Option B — Port to Godot 4 (recommended)
- Domain rewritten in GDScript (or C#) as plain classes — no `Node` dependency.
- Rendering: Godot 2D with `Tween`, `GPUParticles2D`, shaders.
- **Deploy**: `godot --export-release "Web" index.html` → upload static files to any web host. Also gives desktop + Android builds from the same project.
- **Pros**: effects built-in; true static hosting (no server runtime); single codebase → desktop, web, mobile; engine-swap principle naturally enforced by Godot's scene/script split.
- **Cons**: full rewrite from Python; new language (GDScript is close to Python — small learning cost).
- **Dad link**: static files, no backend → copy to `yourserver/brickshooter/` behind nginx. Dead simple.

### Option C — Port to TypeScript + Phaser 3
- Domain in pure TS (unit-testable, no DOM). Rendering in Phaser.
- **Deploy**: `vite build` → static files.
- **Pros**: best web performance; mature particle/tween systems; works on any device with a browser.
- **Cons**: full rewrite + new language; desktop requires Electron wrapper (extra step vs Godot).
- **Dad link**: same as B.

### Recommendation

**Option B (Godot)** best matches the stated goals: effects you can see in Android games (built in), engine-agnostic domain (natural in Godot), and a static-file browser build with no server. Option C is second choice if you prefer a pure-web stack and never need a desktop/mobile build. Option A is only attractive if staying in Python matters more than the other goals.

## 5. Testing strategy

Tests are the load-bearing artefact that lets us port between engines without regressions. The same assertions run against the Python v1 model today and against the GDScript v2 port tomorrow — if both stay green, the port is correct.

| Layer | Framework | What it covers | When it runs |
|---|---|---|---|
| Domain (Python, v1 + v2) | `pytest` | Pure rules: shot validation, resolution cycle, matching, scoring, crossers, refill, history, game-over. No UI. | Locally on save; pre-commit; any CI. Fast (< 1 s). |
| Domain (GDScript, v2) | `GUT` (Godot Unit Test) | Same assertions as Python, translated. Proves the port is behaviourally identical. | Run in Godot editor or headless via `godot --script`. |
| Integration (v2) | GUT scene tests | `ShootBrick` / `Undo` use cases end-to-end against a real `GameNode`, verifying the event stream reaches the presenter. | On demand; CI if set up. |
| Smoke (v2 web) | Playwright or manual checklist | Web build loads, one shot lands, undo reverts, score updates. | Before each deploy to the server. |

### Coverage targets

- **Domain**: every public method of `GameModel` / its v2 equivalent has at least one happy-path and one failure-path test. Already done for v1 (20 cases, committed `4a48300`).
- **Event emission** (added in Phase 1): each domain event type (`BrickShot`, `BrickMoved`, `BrickMatched`, `BrickCrossed`, `LaunchZoneRefilled`, `ScoreChanged`, `StateReverted`, `GameOver`) has at least one test asserting it is emitted in the right situation, in the right order, with the right payload.
- **No coverage %** target — coverage numbers are gameable. Focus is on rules, not lines.

### Running tests

```
# v1
cd v1 && .venv/Scripts/python.exe -m pytest tests/ -v

# v2 domain (Phase 1+)
cd v2 && python -m pytest tests/ -v

# v2 Godot (Phase 2+)
godot --headless --script res://tests/run_all.gd
```

### CI

Deferred until after Phase 2: GitHub Actions workflow that installs Python + runs pytest on `v1/` and `v2/domain/`, then installs Godot and runs GUT on `v2/godot/`. Not required to merge individual phases, but should exist before Phase 3 deploy.

## 6. Phased migration (assuming Option B)

### Target layout

```
v1/                  # frozen, tagged, stays runnable for reference
v2/
  godot/             # Godot project (project.godot, scenes/, scripts/, assets/)
  domain/            # Phase 1 pure-Python domain (skip if going straight to GDScript)
  tests/             # Python unit tests run against domain/; ports become the spec
                     #   GDScript tests live in v2/godot/tests/ (GUT framework)
docs/                # design, plan, TODO
```

Keeping `domain/` and `tests/` in Python under `v2/` lets rules be verified without opening Godot; the GDScript port checks against the same assertions. If Phase 1 is skipped, `v2/` contains only `godot/`.

### Phase 0 — Lock in v1 as a reference
- Tag v1 (`git tag v1-final`) before any rewrite.
- Add a minimal test harness in Python: snapshot tests of `GameModel.movement_resolution_step`, `find_and_remove_groups`, `shoot_brick` on known boards. These become the *spec* the Godot port must match.
- Deliverable: green test suite confirming current behavior.

### Phase 1 — Extract the pure domain (still in Python)
- New `v1/domain/` package with **zero** Kivy imports. Move: `Brick`, `CellIntention`, `FIELD_SIZE`, resolution cycle, matching, shot rules, scoring, history.
- Introduce `DomainEvent` and refactor model methods to return event lists instead of mutating and relying on the view to guess.
- Controller consumes events, translates to Kivy calls.
- **Why this phase exists even if we go Godot**: it proves the event model against the tests from Phase 0 before translating to GDScript. Catches design bugs cheap.
- Deliverable: Kivy game still runs, but domain is now a pure library that could be unit-tested without a window.

### Phase 2 — Port to Godot project at `v2/godot/`
- Translate `v2/domain/` to GDScript classes one entity at a time, porting tests alongside under `v2/godot/tests/` (GUT framework).
- Build minimal scene: grid, brick sprite, launch indicators. Hook domain events → node updates.
- Replace ghost-trail hack with `GPUParticles2D` on move events; particle burst on `BrickMatched`.
- Deliverable: playable Godot desktop build with parity to v1.

### Phase 3 — Web export + server deploy
- `godot --export-release "Web"` → `build/web/`.
- nginx config: serve `build/web/` at `/brickshooter/` with correct COOP/COEP headers (Godot 4 web needs cross-origin isolation for threads).
- TLS via Let's Encrypt if not already set up.
- Test on dad's phone/PC.
- Deliverable: a URL dad can open.

### Phase 4 — Polish
- Mobile touch tuning (larger launch-trigger hitboxes).
- Persistence (score via `localStorage`).
- Optional: Android APK export from same project.

## 7. Risks & open questions

- **Godot web build size**: ~15–30 MB first load. Acceptable for a personal deploy; gzip + caching make revisits instant.
- **Browser audio autoplay**: Godot web requires user gesture before audio. Standard workaround (splash screen).
- **GDScript vs C#**: GDScript is closer to Python and keeps deploy simple; C# web export is newer and less battle-tested. Recommend GDScript unless a reason appears.
- **Effort estimate**: Phase 0: 2–4 h. Phase 1: ~1 day. Phase 2: 2–3 days. Phase 3: 2–4 h. Phase 4: open-ended.

## 8. Decisions needed before starting

1. **Engine**: Godot (B) / Phaser+TS (C) / Python server (A) — default recommendation is B.
2. **Phase 1 included?** I recommend yes, because it validates the event model cheaply; but if you're confident in the port, we can go straight from v1 tests to GDScript.
3. **Hosting details** for Phase 3: domain name, existing web server (nginx/caddy/etc.), TLS setup — needed to write the exact deploy recipe.
4. **Scope for v2**: parity with v1, or also add features (levels, SFX, leaderboard, ...)?

Once these are answered, I'll expand the chosen phase into concrete per-file tasks.
