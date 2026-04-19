# BrickShooter

A colour-match puzzle — launch bricks from the edges into a 10×10 play area, line up three or more of a colour, clear the board, advance. Originally a 1990s Delphi game; this repo holds two Python/web reimplementations of the same rules.

**Play it: [http://your-server.example.com:8000/](http://your-server.example.com:8000/)**

---

## Repository layout

```
v1/              # frozen Kivy desktop reference (Python 3.10, Kivy 2.3)
v2/              # active web port
  domain/          # pure-Python rules (no framework imports)
  backend/         # FastAPI + uvicorn + WebSocket
  frontend/        # TypeScript + Vite + Phaser 4
  tests/           # pytest
docs/            # architecture plan, deployment record, effects plan
deploy/          # systemd unit, config.env example, VDS deploy README
```

- **v1** is tagged `v1-final` and stays runnable as a visual reference for the port. No new work goes there.
- **v2** is the current release (tagged `v2.0.0`) and what's live at the URL above.

---

## Playing

- Open the URL on any modern browser. First visit asks for a display name (stored locally).
- Pick a difficulty in the bottom-right corner — Easy (5 colours), Normal (7), Hard (9).
- Click an edge cell adjacent to the 10×10 play area to fire the innermost brick in that launcher into the field.
- The shot brick travels in its launched direction until it hits another brick. Groups of 3+ same colour clear.
- Clear the whole play area to advance to the next level; the next level starts with one more obstacle, score carries over.
- Game ends only when no valid shot is possible. Final score + level land on the global scoreboard.
- **Controls** live in the four corners of the board: name / level+score+Scores / undo / difficulty+New Game.

---

## Architecture (v2)

Ports & Adapters. The domain owns rules; everything else is a thin adapter that drives it.

```
DOMAIN                    // v2/domain/
  Brick, CellIntention,
  Game (field + score + level + history)
  Rules: movement, matching, shot, crosser, refill
  emits DomainEvent: BrickShot | BrickMoved | BrickMatched
                   | BrickCrossed | LaunchZoneRefilled
                   | ScoreChanged | LevelCleared
                   | StateReverted | GameOver
   ▲                                           │
   │ GameInputPort                             │ GamePresenterPort
   │                                           ▼
BACKEND ADAPTER          // v2/backend/adapters/
   WebInput: WS JSON -> GameInputPort
   WebPresenter: DomainEvent -> JSON frame
FASTAPI                  // v2/backend/app.py
   /ws endpoint; static mount for v2/frontend/dist
FRONTEND                 // v2/frontend/src/
   GameSocket transport, Phaser GridScene,
   sfx + effects (motion blur, halo, particles, confetti)
```

Design notes worth keeping in mind:

- **Sessions** live in memory on the server, keyed by a `sid` the client stores in `localStorage`. F5 resumes the exact game state; server restart loses everything (acceptable for a hobby deploy).
- **Events** flow one-way after connect: client sends `{shoot, undo, new_game, set_name, snapshot, scores}`; server sends a `session` frame, a `snapshot`, then any number of `DomainEvent`s, and optional `scores` replies.
- **Scoreboard** is server-side at `/var/lib/brickshooter/scores.json`. Global, top-50 per difficulty, atomic writes.
- **Per-session gameplay logs** under `journalctl -u brickshooter | grep sid=XYZ` — every inbound message, every emitted event, every snapshot hash. Set `BRICKSHOOTER_LOG_LEVEL=DEBUG` for full field dumps on each snapshot.

---

## Local development

### v2 (active)

Two venvs / node:

```bash
# one-time
cd v2 && py -3.10 -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements-dev.txt
cd v2/frontend && npm ci

# run backend on :8000
cd v2 && .venv/Scripts/python.exe -m backend --port 8000

# in another terminal: run Vite dev server on :5173
cd v2/frontend && npm run dev
```

Open [http://localhost:5173/](http://localhost:5173/). Vite HMR picks up TS/HTML/CSS changes; Python changes need `--reload` on uvicorn or a restart.

Tests:

```bash
cd v2 && .venv/Scripts/python.exe -m pytest tests/ -v   # 188+ cases
cd v2/frontend && npm test                              # Vitest
cd v2/frontend && npm run typecheck                     # tsc --noEmit
```

### v1 (reference only)

```bash
cd v1 && py -3.10 -m venv .venv && .venv/Scripts/python.exe -m pip install -r requirements.txt
cd v1 && .venv/Scripts/python.exe main.py
```

---

## Deploy

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the recorded state of the live VDS (paths, systemd unit, env vars, operations recipes) and [`deploy/README.md`](deploy/README.md) for the generic install recipe.

Update cycle is:

```bash
cd v2/frontend && npm run build
pscp -i ~/.ssh/your-key.ppk -r v2/backend       root@<YOUR-SERVER>:/opt/brickshooter/
pscp -i ~/.ssh/your-key.ppk -r v2/domain        root@<YOUR-SERVER>:/opt/brickshooter/
pscp -i ~/.ssh/your-key.ppk -r v2/frontend/dist/* root@<YOUR-SERVER>:/opt/brickshooter/frontend/
ssh root@<YOUR-SERVER> systemctl restart brickshooter
```

Server has no nginx, no TLS, one systemd unit running uvicorn as an unprivileged user under `ProtectSystem=strict` with a 256 MiB memory cap.

---

## Documentation

- [`docs/MIGRATION_PLAN.md`](docs/MIGRATION_PLAN.md) — the architecture plan that drove the v1→v2 port, annotated with commit hashes for every phase.
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — live VDS layout, systemd config, operator recipes, attack-surface notes.
- [`docs/EFFECTS_PLAN.md`](docs/EFFECTS_PLAN.md) — phased plan for visual effects (particles, motion blur, halo, confetti, score popups, audio).
- [`docs/DESIGN.md`](docs/DESIGN.md) — original game-design document describing the rules and resolution cycle.
- [`docs/TODO.md`](docs/TODO.md) — old v1 checklist (kept for history).

---

## History

- **v1** — Delphi → Python/Kivy port. Playable desktop app, MVC architecture, Cyrillic commit messages. Tagged `v1-final`.
- **v2.0.0** — Full web rewrite: pure-Python domain, FastAPI/WebSocket backend, TypeScript/Phaser frontend. Clean ports & adapters so the same rules could drive a future Qt/pywebview/Godot front-end without domain changes. Deployed on the user's existing VDS alongside a VPN stack, HTTP-only on port 8000.
- **Post-v2.0.0** — Visual effects track (see `docs/EFFECTS_PLAN.md`). Currently shipped: match particles, screen shake, shot flash, motion blur, brick-coloured halo, level-clear confetti, score popups, combo counter, synth SFX with mute.

---

## License

MIT. See each source tree for full dependency licences.
