# Deploying BrickShooter to a VDS

Target: a Linux box (Debian/Ubuntu), systemd, single public port, no nginx.

## Layout

```
/opt/brickshooter/
  ├─ backend/                              # v2/backend/ (Python code)
  ├─ frontend/                             # v2/frontend/dist/ (vite build)
  └─ venv/                                 # Python venv
/var/lib/brickshooter/                     # reserved for future mutable state
/etc/brickshooter/config.env               # env vars (copy from config.env.example)
/etc/systemd/system/brickshooter.service   # copy from brickshooter.service
```

Logs go to journald: `journalctl -u brickshooter -f`.

Gameplay lines are tagged per session. To extract dad's run for investigation:

```bash
# Find his session id from the JOIN line matching his IP:
journalctl -u brickshooter --since "1 hour ago" | grep JOIN
# Then pull that session's full trace:
journalctl -u brickshooter --since "1 hour ago" | grep sid=XYZ > dad-session.log
```

Each line has one of these shapes:

```
JOIN     sid=XYZ client=IP:PORT
LEAVE    sid=XYZ
EVICT    sid=XYZ                       (idle-TTL eviction)
IN       sid=XYZ msg={...}             (every incoming WS message)
OUT      sid=XYZ ev=EventName payload={...}   (every emitted DomainEvent)
SNAPSHOT sid=XYZ score=N hash=H [field=...]
```

Setting `BRICKSHOOTER_LOG_LEVEL=DEBUG` in `config.env` adds the full field
to every SNAPSHOT line (~500 bytes each), so you can reconstruct the exact
board at any moment without replaying events.

## One-time setup

```bash
# Dedicated unprivileged user.
sudo useradd -r -s /usr/sbin/nologin brickshooter

# Directories.
sudo mkdir -p /opt/brickshooter /var/lib/brickshooter /etc/brickshooter
sudo chown brickshooter:brickshooter /var/lib/brickshooter

# Python venv + runtime deps.
sudo python3.10 -m venv /opt/brickshooter/venv
sudo /opt/brickshooter/venv/bin/pip install --upgrade pip
sudo /opt/brickshooter/venv/bin/pip install \
    fastapi 'uvicorn[standard]' websockets
```

## Build + upload from your workstation

```bash
# Build the frontend static bundle.
cd v2/frontend && npm ci && npm run build

# Copy code + build to the server.
rsync -a --delete v2/backend/          server:/opt/brickshooter/backend/
rsync -a --delete v2/frontend/dist/    server:/opt/brickshooter/frontend/

# First-time: install the service file + config.
scp deploy/brickshooter.service server:/etc/systemd/system/
scp deploy/config.env.example   server:/etc/brickshooter/config.env
```

Edit `/etc/brickshooter/config.env` on the server (set `PORT`, tune caps).

## Enable + run

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now brickshooter
sudo systemctl status brickshooter
```

## Firewall

Open only what's needed:

```bash
sudo ufw allow 22/tcp          # or your custom SSH port
sudo ufw allow 8000/tcp        # or whatever PORT you set
sudo ufw enable
```

For WAN abuse protection (optional): front the service with a Cloudflare
tunnel; Cloudflare's DDoS protection handles floods without you touching
server config.

## Update cycle

```bash
# After a code change:
cd v2/frontend && npm run build
rsync -a --delete v2/backend/       server:/opt/brickshooter/backend/
rsync -a --delete v2/frontend/dist/ server:/opt/brickshooter/frontend/
ssh server sudo systemctl restart brickshooter
```

## Smoke test

Open `http://yourserver:PORT/` in a browser. Play a round, press F5,
confirm the board and score survived.

## Attack surface (recap)

- WS frame size capped at `WS_MAX_SIZE` bytes (default 64 KiB).
- Concurrent games capped at `BRICKSHOOTER_MAX_SESSIONS` (default 64).
- Idle games evicted after `BRICKSHOOTER_SESSION_TTL_S` seconds.
- Malformed messages produce `{"type":"error"}` and don't close the socket.
- Static mount on `/` uses FastAPI `StaticFiles` which rejects path traversal.
- Process runs as an unprivileged user with systemd hardening
  (`ProtectSystem=strict`, `ProtectHome=yes`, `NoNewPrivileges=yes`,
  read-only FS except `/var/lib/brickshooter`).
- No cookies, no PII, no auth — URL leak == anyone can play. If you want
  to restrict access, add a token check in the WS handler.
