"""FastAPI app — serves the game over a WebSocket.

Games are kept alive in an in-memory session dict keyed by a `sid` the client
stores in localStorage. On reconnect with the same sid the existing Game is
reused — field, score, undo history all survive an F5. Unknown or stale sids
produce a fresh Game. Server restart wipes everything (in-memory only);
acceptable for a hobby deploy.

On connect the server sends `{type: "session", id: sid}` so the client can
save it, followed by a snapshot. Unknown input messages produce an
`{type: "error"}` frame without closing the socket.

Hardening against the public port:
  - idle sessions evicted after SESSION_TTL_S seconds of no activity
  - max MAX_SESSIONS concurrent sessions; new connections beyond that get
    an error frame and are closed
"""

import os
import time
import uuid
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles

from domain.game import Game

from .adapters.snapshot import encode_snapshot
from .adapters.web_input import WebInput
from .adapters.web_presenter import WebPresenter


app = FastAPI()

DIFFICULTY_COLORS: dict[str, int] = {"easy": 5, "normal": 7, "hard": 9}
DEFAULT_DIFFICULTY = "normal"

MAX_SESSIONS = int(os.environ.get("BRICKSHOOTER_MAX_SESSIONS", "64"))
SESSION_TTL_S = int(os.environ.get("BRICKSHOOTER_SESSION_TTL_S", "1800"))  # 30 min


class _Session:
    __slots__ = ("game", "last_seen")

    def __init__(self, game: Game) -> None:
        self.game = game
        self.last_seen = time.monotonic()

    def touch(self) -> None:
        self.last_seen = time.monotonic()


SESSIONS: dict[str, _Session] = {}


def _evict_idle_sessions(now: float | None = None) -> None:
    if now is None:
        now = time.monotonic()
    stale = [sid for sid, s in SESSIONS.items() if now - s.last_seen > SESSION_TTL_S]
    for sid in stale:
        SESSIONS.pop(sid, None)


def _new_game(difficulty: str) -> Game:
    num_colors = DIFFICULTY_COLORS.get(difficulty, DIFFICULTY_COLORS[DEFAULT_DIFFICULTY])
    game = Game(num_colors=num_colors)
    game.new_game()
    return game


def _get_or_create_session(sid: str | None, difficulty: str = DEFAULT_DIFFICULTY) -> tuple[str, _Session] | None:
    """Returns (sid, session), or None if MAX_SESSIONS is exceeded."""
    _evict_idle_sessions()
    if sid is not None and sid in SESSIONS:
        session = SESSIONS[sid]
        session.touch()
        return sid, session
    if len(SESSIONS) >= MAX_SESSIONS:
        return None
    new_sid = uuid.uuid4().hex
    session = _Session(_new_game(difficulty))
    SESSIONS[new_sid] = session
    return new_sid, session


@app.websocket("/ws")
async def game_ws(ws: WebSocket) -> None:
    await ws.accept()

    requested_sid = ws.query_params.get("sid")
    result = _get_or_create_session(requested_sid)
    if result is None:
        await ws.send_json({"type": "error", "message": "server busy — try again later"})
        await ws.close(code=1013)  # try again later
        return

    sid, session = result
    game = session.game
    presenter = WebPresenter()
    router = WebInput(game)

    await ws.send_json({"type": "session", "id": sid})
    await ws.send_json(encode_snapshot(game))

    try:
        while True:
            message = await ws.receive_json()
            session.touch()
            msg_type = message.get("type") if isinstance(message, dict) else None

            # Protocol-level request for a full state dump. Not a game input.
            if msg_type == "snapshot":
                await ws.send_json(encode_snapshot(game))
                continue

            # A new_game with a difficulty payload swaps the underlying Game
            # for one with the requested num_colors. Without a payload, the
            # existing Game is reused and just reset — keeps undo history
            # conventions matching the domain's new_game.
            if msg_type == "new_game" and isinstance(message.get("difficulty"), str):
                game = _new_game(message["difficulty"])
                session.game = game
                router = WebInput(game)
                presenter = WebPresenter()
                await ws.send_json(encode_snapshot(game))
                continue

            try:
                events = router.handle_message(message)
            except ValueError as exc:
                await ws.send_json({"type": "error", "message": str(exc)})
                continue

            for event in events:
                presenter.on_event(event)
            for frame in presenter.drain():
                await ws.send_json(frame)

            # new_game resets state; undo restores an older state. In both
            # cases the client needs a fresh snapshot to avoid drift — rebuilding
            # from events alone is error-prone across these transitions.
            reverted = any(type(e).__name__ == "StateReverted" for e in events)
            if msg_type == "new_game" or reverted:
                await ws.send_json(encode_snapshot(game))

    except WebSocketDisconnect:
        return


# Static mount for the production build. Looked up from BRICKSHOOTER_FRONTEND_DIR
# if set, otherwise the relative sibling path used in dev. Missing dir = don't
# mount; /ws still works. In dev you'd run Vite on :5173 instead.
_frontend_dir = Path(
    os.environ.get(
        "BRICKSHOOTER_FRONTEND_DIR",
        str(Path(__file__).resolve().parent.parent / "frontend" / "dist"),
    )
)
if _frontend_dir.is_dir():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="static")
