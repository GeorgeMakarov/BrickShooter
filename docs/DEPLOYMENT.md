# BrickShooter — Deployment Overview

Single-process deploy: one `uvicorn` unit under systemd, HTTP only, no
nginx, no TLS, plain port. Good fit for a personal VDS shared with other
services (UDP VPNs, DNS, etc.) because the game uses a single TCP port
that's trivial to pick and because the process is sandboxed via systemd
hardening (unprivileged user, `ProtectSystem=strict`, memory cap).

The concrete recipe is in [`../deploy/README.md`](../deploy/README.md);
the generic systemd unit template lives at
[`../deploy/brickshooter.service`](../deploy/brickshooter.service) and the
env-var example at
[`../deploy/config.env.example`](../deploy/config.env.example).

Host-specific notes (real IP, hostname, operator SSH recipes) are kept
in an untracked `docs/DEPLOYMENT.private.md` alongside this file — that
file is gitignored so operational details don't leak to the public repo.
If you fork this project, copy the `.example` to a local-only file of
your own.

## Layout on a deployed box

```
/opt/brickshooter/
  ├─ backend/                       # v2/backend/ tree
  ├─ domain/                        # v2/domain/ tree (sibling — imported as 'from domain...')
  ├─ frontend/                      # contents of v2/frontend/dist/
  └─ venv/                          # Python venv with runtime deps

/var/lib/brickshooter/              # owned by brickshooter user
  └─ scores.json                    # server-side high-score table (atomic writes)
/etc/brickshooter/config.env        # env vars consumed by the systemd unit
/etc/systemd/system/brickshooter.service
```

## Runtime configuration

The full list of env vars and their defaults lives in
`deploy/config.env.example`. Highlights:

| Variable | Default | Purpose |
|---|---|---|
| `HOST` | `0.0.0.0` | uvicorn bind address |
| `PORT` | `8000` | TCP port; make sure it's open on the firewall if any |
| `WS_MAX_SIZE` | `65536` | inbound WS frame size cap (DoS mitigation) |
| `BRICKSHOOTER_MAX_SESSIONS` | `64` | concurrent Game cap |
| `BRICKSHOOTER_SESSION_TTL_S` | `1800` | idle-session eviction |
| `BRICKSHOOTER_FRONTEND_DIR` | `/opt/brickshooter/frontend` | path to the built Vite bundle |
| `BRICKSHOOTER_SCORES_FILE` | `/var/lib/brickshooter/scores.json` | high-score persistence |
| `BRICKSHOOTER_LOG_LEVEL` | `INFO` | `DEBUG` additionally dumps full field on every snapshot |
| `BRICKSHOOTER_LOG_FILE` | unset | optional path for a rotating file handler (otherwise stderr → journald) |

## Operation recipes (generic — substitute your own host/key)

```bash
# Status + logs:
ssh <user>@<your-server> "systemctl status brickshooter"
ssh <user>@<your-server> "journalctl -u brickshooter -f"

# Pull a single player's session for bug investigation:
ssh <user>@<your-server> \
    "journalctl -u brickshooter --since '2 hours ago' | grep sid=XYZ" > session.log

# Restart / stop / disable:
ssh <user>@<your-server> "systemctl restart brickshooter"
ssh <user>@<your-server> "systemctl stop brickshooter"
ssh <user>@<your-server> "systemctl disable brickshooter"
```

## Update cycle

From the repo root on your workstation:

```bash
cd v2/frontend && npm run build && cd ../..

rsync -a v2/backend       <user>@<your-server>:/opt/brickshooter/
rsync -a v2/domain        <user>@<your-server>:/opt/brickshooter/
rsync -a v2/frontend/dist/ <user>@<your-server>:/opt/brickshooter/frontend/

ssh <user>@<your-server> \
    "find /opt/brickshooter -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; systemctl restart brickshooter"
```

If `deploy/brickshooter.service` changed too:

```bash
rsync deploy/brickshooter.service <user>@<your-server>:/etc/systemd/system/brickshooter.service
ssh <user>@<your-server> "systemctl daemon-reload && systemctl restart brickshooter"
```

## Gameplay log shape

Every gameplay line begins with `sid=XYZ` so a session can be extracted
with a single grep.

```
JOIN     sid=X client=IP:PORT
LEAVE    sid=X
EVICT    sid=X                              (idle TTL eviction)
IN       sid=X msg={...}                    (every inbound WS frame)
OUT      sid=X ev=EventName payload={...}   (every emitted DomainEvent)
SNAPSHOT sid=X score=N hash=H [field=...]
```

`BRICKSHOOTER_LOG_LEVEL=DEBUG` adds the full 16×16 field to every
`SNAPSHOT` line — replayable state at every decision point.

## Attack-surface notes

No authentication. No cookies, no PII. Anyone with the URL plays. The
game process is isolated from the host via:

- Unprivileged system user (e.g. `brickshooter`) + systemd hardening
  (`ProtectSystem=strict`, `ProtectHome=yes`, `NoNewPrivileges=yes`,
  `PrivateTmp=yes`, `ReadWritePaths` scoped to `/var/lib/brickshooter`).
- `MemoryMax=256M` — the game can't starve other services under abuse.
- `--ws-max-size 65536` (64 KiB) caps inbound WebSocket frames.
- `BRICKSHOOTER_MAX_SESSIONS` + 30-min idle TTL — bounded memory.
- Only the configured TCP port exposed; UDP-based services (VPN, DNS,
  etc.) on the same host aren't affected by collisions because UDP and
  TCP port namespaces are disjoint.

No known escalation path from a compromised game process to host
configuration under normal operation.

## Future improvements (not shipped)

- TLS termination (fine to skip for a personal deploy).
- Rate limiting at the iptables/nftables layer.
- Cloudflare Tunnel front-end for DDoS protection + TLS without local
  cert maintenance.
- pywebview native-window adapter (Phase 5 of the migration plan).
