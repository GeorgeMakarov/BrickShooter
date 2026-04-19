# BrickShooter — Live Deployment

## URL

**http://your-server.example.com:8000/**

Plain HTTP, port 8000, no TLS. Anyone with the URL can play. The hostname resolves to `<YOUR-SERVER>` via an A record in the `my.to` zone.

## Server facts (recorded 2026-04-19)

| | |
|---|---|
| Public URL | `http://your-server.example.com:8000/` |
| Host IP | `<YOUR-SERVER>` (hostname `<your-host>` internally) |
| DNS | `your-server.example.com` A record → `<YOUR-SERVER>` |
| OS | Debian 12 (bookworm), kernel 6.1.158 |
| Python | 3.11.2 at `/usr/bin/python3` |
| SSH key | `~/.ssh/your-key.ppk` (PuTTY format) |
| Other services on the box | OpenVPN (1194/udp), AmneziaWG (51800/udp), Bind9 DNS (53), sing-box (443), mtg (8443), SSH (22) |
| Firewall | iptables INPUT policy = `ACCEPT` (no ufw). No rule needed for 8000. |
| Memory budget | 960 MB total; service capped at 256 MB via systemd `MemoryMax=` |
| Disk usage | Service + deps use ~60 MB; 5+ GB free on root |

## On-server layout

```
/opt/brickshooter/
  ├─ backend/                       # v2/backend/ tree
  ├─ domain/                        # v2/domain/ tree (sibling — imports as 'from domain...')
  ├─ frontend/                      # contents of v2/frontend/dist/
  └─ venv/                          # Python 3.11 venv: fastapi, uvicorn[standard], websockets

/var/lib/brickshooter/              # owned by brickshooter user; reserved for future state
/etc/brickshooter/config.env        # env vars consumed by the systemd unit
/etc/systemd/system/brickshooter.service
```

The unprivileged `brickshooter` system user runs the service (`useradd -r -s /usr/sbin/nologin`).

## systemd unit

Unit ships in `deploy/brickshooter.service`. Key points:

- `WorkingDirectory=/opt/brickshooter` — so `backend` and `domain` are importable as top-level packages.
- `ExecStart=/opt/brickshooter/venv/bin/python -m backend --host ${HOST} --port ${PORT} --ws-max-size ${WS_MAX_SIZE}`
- `Restart=on-failure`, `RestartSec=3`
- Hardening: `NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ProtectHome`, `ReadWritePaths=/var/lib/brickshooter`, `RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6`, `MemoryMax=256M`

## config.env on the server

```
HOST=0.0.0.0
PORT=8000
WS_MAX_SIZE=65536
BRICKSHOOTER_MAX_SESSIONS=64
BRICKSHOOTER_SESSION_TTL_S=1800
BRICKSHOOTER_FRONTEND_DIR=/opt/brickshooter/frontend
BRICKSHOOTER_LOG_LEVEL=INFO
```

## How to operate

```bash
# Status and live logs (from your workstation):
plink -i ~/.ssh/your-key.ppk root@<YOUR-SERVER> "systemctl status brickshooter"
plink -i ~/.ssh/your-key.ppk root@<YOUR-SERVER> "journalctl -u brickshooter -f"

# Pull a single user's session for bug investigation:
plink -i ~/.ssh/your-key.ppk root@<YOUR-SERVER> \
    "journalctl -u brickshooter --since '2 hours ago' | grep sid=XYZ" > dad-session.log

# Restart:
plink -i ~/.ssh/your-key.ppk root@<YOUR-SERVER> "systemctl restart brickshooter"

# Stop / disable:
plink -i ~/.ssh/your-key.ppk root@<YOUR-SERVER> "systemctl stop brickshooter"
plink -i ~/.ssh/your-key.ppk root@<YOUR-SERVER> "systemctl disable brickshooter"
```

## How to update after code changes

From the repo root on your workstation (Git Bash / PowerShell):

```bash
cd v2/frontend && npm run build && cd ../..

pscp -i ~/.ssh/your-key.ppk -batch -r v2/backend \
    root@<YOUR-SERVER>:/opt/brickshooter/
pscp -i ~/.ssh/your-key.ppk -batch -r v2/domain  \
    root@<YOUR-SERVER>:/opt/brickshooter/
pscp -i ~/.ssh/your-key.ppk -batch -r v2/frontend/dist/* \
    root@<YOUR-SERVER>:/opt/brickshooter/frontend/

plink -i ~/.ssh/your-key.ppk -batch root@<YOUR-SERVER> \
    "find /opt/brickshooter -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null; systemctl restart brickshooter"
```

If the `deploy/brickshooter.service` file changed, also:

```bash
pscp -i ~/.ssh/your-key.ppk -batch deploy/brickshooter.service \
    root@<YOUR-SERVER>:/etc/systemd/system/brickshooter.service
plink -i ~/.ssh/your-key.ppk -batch root@<YOUR-SERVER> \
    "systemctl daemon-reload && systemctl restart brickshooter"
```

## Log-line reference

Every gameplay line begins with `sid=XYZ` so a session can be extracted with a single grep.

```
JOIN     sid=X client=IP:PORT
LEAVE    sid=X
EVICT    sid=X                              (idle TTL eviction)
IN       sid=X msg={...}                    (every inbound WS frame)
OUT      sid=X ev=EventName payload={...}   (every emitted DomainEvent)
SNAPSHOT sid=X score=N hash=H [field=...]
```

`BRICKSHOOTER_LOG_LEVEL=DEBUG` in the env file adds the full 16×16 field to every `SNAPSHOT` line — replayable state at every decision point.

## Attack-surface notes

No authentication. No cookies, no PII. Anyone with the URL plays. The game is isolated from the host's VPN services by:

- Unprivileged user (`brickshooter`) with systemd hardening
- `MemoryMax=256M` — cannot starve the VPN services even under sustained abuse
- `--ws-max-size 65536` (64 KiB) caps inbound WS frames
- `MAX_SESSIONS=64` cap + 30-min idle TTL — bounded memory regardless of incoming
- Only TCP port 8000 exposed by the service; all other VPN/DNS ports use different protocols/ports

No known path from the game to the VPN configs under normal operation. A kernel-level compromise of Python could still escape the hardening, but that's a much bigger problem than this service.

## Future improvements (not shipped)

- TLS termination (plain HTTP is fine for a personal deploy).
- Rate limiting at the iptables/nftables layer (today relies only on in-process caps).
- Cloudflare Tunnel front-end for DDoS protection without TLS setup.
- Server-side scoreboard (currently localStorage per browser).
- pywebview native-window adapter (Phase 5 of the migration plan).
