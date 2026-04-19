# BrickShooter — Architecture Migration Plan

## 1. Goals

1. **Engine-swappable**: game rules must run independently of any rendering/transport. The same domain should drive a browser, a native window, or a future Godot/mobile port without edits.
2. **Rich visual effects**: smooth tweens, particles on match/blast, motion trails — backed by a mature effects library rather than hand-rolled ghost spawners.
3. **Browser-playable via a link** (primary deploy): one URL on the user's own server. The **game IS the web server** — a single Python process serves both the frontend bundle and a WebSocket that streams domain events. No nginx.
4. **Run locally as a desktop game**: either serve `localhost:8000` and open the system browser, or plug a native-window adapter (pywebview/Qt/Kivy) into the same domain.
5. **Preserve v1 logic**: reuse rules already debugged in `model.py` (resolution cycle, crossers, refill, matching, scoring, undo).

## 2. Current state (v1)

- **Stack**: Python 3.10 + Kivy 2.3
- **Pattern**: MVC. `model.py` (pure logic, ~430 LOC), `view.py` (Kivy widgets, ~490 LOC), `controller.py` (wiring, ~160 LOC).
- **Strengths**: model is already near-pure (only uses `random`, `copy`, stdlib enum) — close to a clean domain layer.
- **Weaknesses**:
  - View couples rendering, animation choreography, and widget state tracking. Ghost-trail hack leaks widgets.
  - Controller calls view methods directly (`draw_field`, `animate_events`, `update_score`) — no abstraction.
  - `model.save_state` uses `deepcopy(field)` — fine, but not reified as a domain event stream, so the view re-inspects the whole grid after every step.
  - No tests (fixed in Phase 0 — 20 pytest cases now pin v1 behaviour).

## 3. Target architecture: Ports & Adapters, server-authoritative

The domain holds the authoritative game state on the server. Inputs arrive over a WebSocket; outputs (domain events) stream back to one or more connected clients.

```
                      ╔════════════════════════════════════════╗
                      ║              DOMAIN (pure)             ║
                      ║  Brick, CellIntention, Field           ║
                      ║  Rules: shot / movement / match /      ║
                      ║         crosser / refill / history     ║
                      ║  Emits: DomainEvent                    ║
                      ╚════════════════════════════════════════╝
                                        ▲
                          GameInputPort │ GamePresenterPort
                                        ▼
              ╔════════════════════════════════════════════════════╗
              ║              APPLICATION (use cases)               ║
              ║  ShootBrick, Undo, NewGame                         ║
              ╚════════════════════════════════════════════════════╝
                     ▲                                          ▲
                     │                                          │
       ┌─────────────┴──────────┐              ┌────────────────┴────────┐
       │   INPUT ADAPTER        │              │   OUTPUT ADAPTER        │
       │  WS message → port     │              │  event → WS JSON frame  │
       └────────────────────────┘              └─────────────────────────┘
                     ▲                                          │
                     │                                          ▼
                 ┌───┴──────────────────────────────────────────────┐
                 │        FRONTEND (TypeScript + Phaser 3)          │
                 │  WS client, event decoder, game scene, effects   │
                 └──────────────────────────────────────────────────┘
```

A second adapter pair can run the domain locally without the WS — native window (pywebview/Qt/Kivy) implements the presenter port directly in-process. Same domain, different wires.

### Key primitives

- **`DomainEvent`** (frozen dataclasses): `BrickShot`, `BrickMoved`, `BrickMatched`, `BrickCrossed`, `LaunchZoneRefilled`, `ScoreChanged`, `StateReverted`, `GameOver`. *Done* — committed `bdda080`.
- **`GamePresenterPort`**: one method `on_event(DomainEvent)`. Every adapter implements this once.
- **`GameInputPort`**: `shoot(cell)`, `undo()`, `new_game()`. Adapters translate their transport into these calls.
- **Wire format**: JSON mirror of each event dataclass. Single source of truth: event schema generated from Python dataclasses so the TS client types stay in sync.

### Why this helps the effects problem

Events tell the presenter exactly what happened and when. Motion trails, particle bursts on match, score popups become "when `BrickMatched` arrives, emit particles at these cells for 400 ms." Phaser's `Tweens` and `GPUParticles`-equivalent (`ParticleEmitter`) track lifetime for us — no more ghost-spawner leaks.

## 4. Chosen stack (Shape X: Python backend + web frontend)

| Layer | Tech | Role |
|---|---|---|
| Domain | Python 3.10 (stdlib only) | Authoritative rules. Importable from any adapter. |
| Backend server | FastAPI + uvicorn | `/ws` endpoint, static hosting of the frontend bundle. Single process, HTTP only. |
| Transport | WebSocket, JSON frames | Bidirectional event + input stream. One connection per client. |
| Frontend bundler | Vite + TypeScript | Dev server with HMR; `vite build` produces the static bundle the Python app serves. |
| Frontend renderer | Phaser 3 | Particle emitters, tweens, sprite sheets, input handling. Mature. |
| Frontend tests | Vitest (unit) + Playwright (smoke) | Vitest for pure TS (event decoder, transport). Playwright for one end-to-end shot-undo-score cycle. |
| Backend tests | pytest + Starlette `TestClient` | Domain unit tests + WS integration tests that drive a full game over a fake socket. |
| Deployment | Single `uvicorn` process, systemd unit on user's server | No nginx, no TLS — plain HTTP on a port. |

### Why these choices

- **FastAPI + uvicorn**: async WS out of the box; static file mount is one line; widely understood.
- **Phaser 3 over PixiJS/raw canvas**: particles, tweens, input, asset pipeline all built-in — most of what we hand-rolled in Kivy disappears.
- **TypeScript over JS**: the event contract is the seam between server and client; static types catch drift between dataclass fields and JSON keys.
- **Vite**: dev server is fast; production build is a static `dist/` folder the Python app serves verbatim.
- **JSON over WS (not Protobuf/MsgPack)**: payloads are tiny (few hundred bytes per frame), JSON is debuggable with DevTools → no reason to optimise yet.

## 5. Target repository layout

```
v1/                          # frozen, tagged, stays runnable for reference
v2/
  domain/                    # pure rules, no framework imports
    events.py                # DomainEvent variants (done)
    brick.py, constants.py   # moved from v1/model.py during phase 1
    rules/                   # movement, matching, shot, crosser, refill
    history.py
    game.py                  # facade; holds field+score; delegates to rules
    ports.py                 # GameInputPort, GamePresenterPort ABCs
  backend/
    adapters/
      web_presenter.py       # DomainEvent -> JSON frame -> WS
      web_input.py           # WS message -> GameInputPort call
    app.py                   # FastAPI: /ws endpoint + StaticFiles mount
    __main__.py              # `python -m v2.backend`
  frontend/
    src/
      scenes/GridScene.ts    # Phaser scene, brick sprites, effects
      transport/ws_client.ts # opens socket, decodes JSON frames
      transport/events.ts    # TS types mirroring DomainEvent
      main.ts                # boot Phaser game
    public/
    tests/                   # Vitest
    playwright/              # smoke tests
    package.json
    vite.config.ts
  tests/                     # pytest: domain + backend
  conftest.py
docs/
```

## 6. Testing strategy

Same test pyramid as before, updated for this stack.

| Layer | Framework | What it covers | When it runs |
|---|---|---|---|
| Domain (Python) | `pytest` | Pure rules + event emission. | On save, pre-commit, CI. < 1 s. |
| Backend adapters | `pytest` + Starlette `TestClient` | WS presenter serialises events correctly; WS input routes correctly; one full game over a fake socket. | CI, pre-deploy. |
| Frontend units | `vitest` | Event decoder, transport retry/backoff, pure scene-adjacent helpers. | On save, CI. |
| Frontend smoke | `playwright` | Open the deployed URL, fire a shot, see the board change, press undo, see it revert. | Pre-deploy. |

### Working discipline

Write the test **before** the implementation change. Red → green → refactor. No code change lands without a test that would have failed yesterday. Exception: pure mechanical moves (file renames, import-only edits). Test + change on the same commit.

### Coverage targets

- Every public method of the domain has a happy-path and a failure-path test.
- Every `DomainEvent` type has a test asserting it is emitted in the right situation, order, and with the right payload.
- Every WS message direction has a round-trip test (Python emits → TS decoder accepts, and vice versa for input messages).

### Running tests

Each version has its own virtualenv (dependency sets don't overlap — Kivy vs FastAPI/uvicorn).

```
# v1 — pinned for reference
cd v1 && .venv/Scripts/python.exe -m pytest tests/ -v

# v2 — current work
cd v2 && .venv/Scripts/python.exe -m pytest tests/ -v

# frontend (phase 3+)
cd v2/frontend && npm test
cd v2/frontend && npx playwright test
```

Bootstrap a missing venv:

```
cd v2 && py -3.10 -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements-dev.txt
```

### CI (deferred until Phase 4)

GitHub Actions: pytest on `v2/`, `vitest` on `v2/frontend/`, Playwright on a locally-booted backend. Not required to merge individual sub-tasks.

## 7. Phased migration

### Phase 0 — Lock in v1 as a reference *(done)*
- `v1-final` tag (`48ab5a7`).
- 20 pytest cases in `v1/tests/test_model.py` (`4a48300`).

### Phase 1 — Extract the pure Python domain *(done)*

Target: `v2/domain/` with zero framework imports, emitting `DomainEvent` streams. Each rule is a pure function (or small class) that mutates a `field` in place and returns `list[DomainEvent]`. Randomness is injected (see `refill.pick_color`) to keep tests deterministic. 80 pytest cases currently green.

| # | Sub-task | Status | Commit |
|---|---|---|---|
| 1 | `DomainEvent` types (frozen dataclasses, tagged union) | done | `bdda080` |
| 2 | Move `Brick`, `CellIntention`, constants to `v2/domain/` | done | `dd55ca6` |
| 3 | Matching rule → `BrickMatched` events | done | `8fe4dbe` |
| 4 | Movement rule → `BrickMoved` events | done | `1ba40fe` |
| 5a | Shot rule → `BrickShot` event | done | `1b0a95d` |
| 5b | Crosser rule → `BrickCrossed` events | done | `6fed217` |
| 5c | Refill rule → `BrickMoved` + `LaunchZoneRefilled` | done | `d1ccadb` |
| 6 | `HistoryStack` → `StateReverted` on revert | done | `4374e5f` |
| 7 | Ports (`GameInputPort`/`GamePresenterPort`) + `can_shoot` + `Game` facade orchestrating resolution cycle, score, game-over | done | *this commit* |
| 8 | Domain integration test: drive `Game` through a full shot→resolve→undo round with a fake `GamePresenterPort`, assert the event stream end-to-end. (v1 stays frozen as the visual reference — no controller rewire.) | done | *this commit* |

Exit criterion: `pytest v2/tests/` green, including the end-to-end integration test that drives a full game round via `Game` + a fake presenter. v1 remains frozen at `v1-final` as the visual reference.

### Phase 2 — Backend adapter (FastAPI + WS) *(done)*

| # | Sub-task | Status | Commit |
|---|---|---|---|
| 1 | JSON codec (`to_json` / `from_json`) for every `DomainEvent` | done | `aa5d6d2` |
| 2 | `WebPresenter` implementing `GamePresenterPort`, buffers JSON frames for async flush | done | `e603a50` |
| 3 | `WebInput` parsing `{shoot, undo, new_game}` messages into `GameInputPort` calls | done | `75ffe77` |
| 4 | Snapshot encoder + FastAPI `/ws` endpoint; end-to-end test via Starlette `TestClient` | done | *this commit* |
| 5 | `python -m backend` entry point (uvicorn); live smoke check | done | *this commit* |

Exit criterion met: `python -m backend --port 8765` serves a WS at `ws://127.0.0.1:8765/ws`. A live client receives a snapshot on connect, a fresh snapshot after `new_game`, and event frames after shots. Static file mount for the frontend bundle deferred to Phase 4.

### Phase 3 — Frontend (TypeScript + Phaser 4) *(done)*

| # | Sub-task | Status | Commit |
|---|---|---|---|
| 1 | TS event-type mirror + `decodeEvent` | done | `67e2a54` |
| 2 | `GameSocket` WS client (snapshot + event routing, reconnect) | done | `94dfaf0` |
| 3 | Pure `renderSnapshot` → `SpriteLayer` | done | `d580250` |
| 4 | `dispatchEvent` → `SceneEffects` (per-variant mapping, exhaustive) | done | `f90c611` |
| 5 | Phaser `GridScene` implementing SpriteLayer + SceneEffects (tween on move, particle burst on match, fade-in on refill, launcher flash on shot) | done | *this commit* |
| 6 | Pointer input on launcher cells → `shoot` messages; DOM buttons for `undo`/`new_game`; DOM overlay for game-over | done | *this commit* |

Exit criterion met: `python -m backend --port 8000` + `npm run dev` in `v2/frontend/` → browser loads the game, shots animate, matches burst, undo reverts, new-game resets. 32 vitest cases + 151 pytest cases green.

### Phase 4 — Packaging and deploy *(done)*

Actual deployment recorded in `docs/DEPLOYMENT.md`. The recipe below is the
general template; the live server ran a slightly-adjusted version (Python 3.11
instead of 3.10 — only what was already on the box) and needed no firewall
changes because the host's iptables INPUT policy was already `ACCEPT`.

#### Pre-deploy (features that only affect backend/frontend, no infra changes)

1. **Harden the backend** — add quotas for the public port:
   - `--ws-max-size` limit (64 KiB, down from uvicorn's 16 MiB default)
   - `MAX_SESSIONS` cap; reject new sessions when full
   - Idle-session eviction on a TTL (default 30 min of no WS activity)
2. **Difficulty presets** — `new_game` payload gains a `difficulty` field; three presets tune `num_colors` (Easy 5, Normal 7, Hard 9).
3. **Scoreboard** — localStorage top-10 per browser, shown in the game-over overlay and a "Scores" button. Server stays stateless w.r.t. scores for now.
4. **Frontend production build** — `npm run build` produces `v2/frontend/dist/`; FastAPI mounts it at `/` via `StaticFiles` so a single process serves the bundle + the `/ws` endpoint. In dev, Vite still serves at `:5173` and talks to `:8000` directly.

#### Server layout (FHS-style on the VDS)

```
/opt/brickshooter/                         # app code (owned by root, world-readable)
  ├─ backend/                              # v2/backend/ tree
  ├─ frontend/                             # v2/frontend/dist/ (built bundle)
  └─ venv/                                 # Python venv with runtime deps

/var/lib/brickshooter/                     # mutable data (owned by brickshooter user)
  └─ (reserved for future server-side state; nothing yet — scores are localStorage)

/etc/brickshooter/config.env               # env vars: PORT, MAX_SESSIONS, SESSION_TTL_S
/etc/systemd/system/brickshooter.service   # systemd unit
```

Logs go to journald (`journalctl -u brickshooter`). No `/var/log/brickshooter/`.

#### systemd unit

Repo ships a template at `deploy/brickshooter.service`. Key flags:

```
[Service]
User=brickshooter
Group=brickshooter
EnvironmentFile=/etc/brickshooter/config.env
ExecStart=/opt/brickshooter/venv/bin/python -m backend \
    --host 0.0.0.0 --port ${PORT} --ws-max-size 65536
Restart=on-failure
RestartSec=3

# Hardening
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/lib/brickshooter
ProtectKernelTunables=yes
ProtectKernelModules=yes
RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
```

#### Deploy steps

1. Create user: `useradd -r -s /usr/sbin/nologin brickshooter`.
2. `mkdir -p /opt/brickshooter /var/lib/brickshooter /etc/brickshooter`.
3. `rsync -a v2/backend /opt/brickshooter/ && rsync -a v2/frontend/dist /opt/brickshooter/frontend/`.
4. `python3 -m venv /opt/brickshooter/venv && /opt/brickshooter/venv/bin/pip install fastapi 'uvicorn[standard]' websockets` — 3.10+ is enough; 3.11 is what Debian 12 ships.
5. Drop `deploy/brickshooter.service` at `/etc/systemd/system/` and `deploy/config.env.example` at `/etc/brickshooter/config.env`.
6. `systemctl daemon-reload && systemctl enable --now brickshooter`.
7. Firewall: if the host runs ufw/nftables with a default-deny INPUT policy, add a rule allowing `${PORT}/tcp`. If INPUT is `ACCEPT` by default (as on the live VDS), no change is needed — the service becomes reachable as soon as it binds.
8. **Smoke test**: open the URL from another device, play a round, F5 and confirm state persists.

#### Attack-surface analysis

| Attack | Mitigation (shipped in this phase) |
|---|---|
| Giant WS frame exhausts memory | `--ws-max-size 65536` caps inbound frame size |
| Flooding new sessions | `MAX_SESSIONS` cap + idle-session TTL; refuse beyond the cap with a clear error frame |
| Crafted input crashes parser | `WebInput` already rejects with `ValueError` and replies with `{"type":"error"}` without closing |
| Path traversal on static mount | FastAPI `StaticFiles` rejects `..` traversals by default |
| Process compromise → host damage | systemd hardening (`ProtectSystem=strict`, unprivileged user, no extra caps) |
| Network abuse / floods | UFW/nftables rate limit on the game port; optional Cloudflare free tier in front |
| Unauthenticated play (URL leak) | Deliberate: no auth, no PII. If restricted access wanted later, add a query-param token check in the WS handler. |

#### Exit criterion

Dad opens the URL, plays a round, closes the tab; next day opens the URL again and sees his previous state waiting. `systemctl status brickshooter` green, `journalctl -u brickshooter` shows clean logs.

### Phase 5 — Native window adapter (optional) *(not started)*

Second presenter adapter that implements `GamePresenterPort` against a local UI toolkit. Options, cheapest first:

- **pywebview**: bundles the same frontend `dist/` into a native window. Near-zero additional code; no browser chrome.
- **Qt/PySide6**: proper native widgets. More work, but feels like a desktop app.
- **Refactor v1 Kivy** to implement the port. Most code re-use, but carries the Kivy dependency forward.

Exit criterion: `python -m v2.desktop` opens a window that plays the same game without needing a running server.

### Phase 6 — Polish *(done; session mechanics + server scoreboard + UI layout)*

Shipped during migration:
- Level progression (clearing the play area bumps level, bricks++, score persists)
- Server-side scoreboard at `/var/lib/brickshooter/scores.json`
- In-app name prompt + editable name chip
- Corner layout: level / score / scores / name / undo / new-game / difficulty all in the previously-unused 3×3 corner regions
- Per-session gameplay logging for post-hoc investigation

Deferred to a follow-on track:
- Visual effects polish (particles, shake, trails, combo feedback) — see `docs/EFFECTS_PLAN.md`
- SFX
- PWA manifest
- Mobile touch tuning

## Migration complete

Tagged **`v2.0.0`** (commit `TBD`) — first stable release of the v2 web codebase. v1 remains frozen at `v1-final` as the visual reference. All phases 0–4 done; Phase 5 (native window) is optional and not started.

## 8. Risks & open questions

- **Server uptime**: the game needs the Python process alive. systemd with `Restart=always` covers crashes; host reboots are on the user.
- **WS latency** over WAN: 30–80 ms RTT for input → event echo. Acceptable for a turn-based puzzle; unacceptable for twitch action. Current game is turn-based, so fine.
- **Concurrency**: one `Game` instance per WS connection, held in memory on the server. Trivial for single-user; if dad and others play simultaneously, fine; if it ever becomes multi-user-per-room, revisit.
- **Effort estimate** (from here): Phase 1 remaining: 1–1.5 days. Phase 2: 1 day. Phase 3: 2–3 days. Phase 4: 2–4 h (plain HTTP). Phase 5: half a day with pywebview.

## 9. Decisions

All decided:
- Stack: Python backend + TypeScript/Phaser frontend, one process serves both. (Shape X.)
- No Godot, no nginx, no TLS — plain HTTP on a port.
- Scope for v2: parity with v1 + visual effects. No new features (levels, SFX, leaderboard, etc.) in this migration.
- Phase 1: included (in progress, sub-task 1 done).
- Phase 5 native window: **pywebview**. Cheapest path to a local desktop shell; reuses the web frontend verbatim; engine-swap principle is already exercised by v1 Kivy sitting alongside v2 web.
