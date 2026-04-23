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
from .game_log import (
    log_evict,
    log_in,
    log_join,
    log_leave,
    log_out,
    log_snapshot,
)
from .scoreboard import ScoreBoard, MAX_NAME_LENGTH
from dataclasses import asdict as _asdict
from pathlib import Path as _Path


app = FastAPI()

DIFFICULTY_COLORS: dict[str, int] = {"easy": 5, "normal": 7, "hard": 9}
DEFAULT_DIFFICULTY = "normal"

MAX_SESSIONS = int(os.environ.get("BRICKSHOOTER_MAX_SESSIONS", "64"))
SESSION_TTL_S = int(os.environ.get("BRICKSHOOTER_SESSION_TTL_S", "604800"))  # 7 days


class _Session:
    __slots__ = ("game", "last_seen", "name", "difficulty")

    def __init__(self, game: Game, difficulty: str) -> None:
        self.game = game
        self.last_seen = time.monotonic()
        self.name: str = "Anonymous"
        self.difficulty: str = difficulty

    def touch(self) -> None:
        self.last_seen = time.monotonic()


SESSIONS: dict[str, _Session] = {}

_SCORES_PATH = _Path(
    os.environ.get("BRICKSHOOTER_SCORES_FILE", "/var/lib/brickshooter/scores.json")
)
SCOREBOARD = ScoreBoard(_SCORES_PATH)


def _evict_idle_sessions(now: float | None = None) -> None:
    if now is None:
        now = time.monotonic()
    stale = [sid for sid, s in SESSIONS.items() if now - s.last_seen > SESSION_TTL_S]
    for sid in stale:
        SESSIONS.pop(sid, None)
        log_evict(sid)


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
    session = _Session(_new_game(difficulty), difficulty)
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

    client = f"{ws.client.host}:{ws.client.port}" if ws.client else "unknown"
    log_join(sid, client)

    await ws.send_json({"type": "session", "id": sid})
    await ws.send_json(encode_snapshot(game))
    log_snapshot(sid, game)

    try:
        while True:
            message = await ws.receive_json()
            session.touch()
            log_in(sid, message)
            msg_type = message.get("type") if isinstance(message, dict) else None

            # Protocol-level request for a full state dump. Not a game input.
            if msg_type == "snapshot":
                await ws.send_json(encode_snapshot(game))
                log_snapshot(sid, game)
                continue

            # Register / update the player's display name for score records.
            if msg_type == "set_name":
                raw = message.get("name", "")
                if isinstance(raw, str):
                    session.name = raw.strip()[:MAX_NAME_LENGTH] or "Anonymous"
                continue

            # Scoreboard query. Reply with top-N for the requested difficulty
            # (defaults to the session's current difficulty).
            if msg_type == "scores":
                requested = message.get("difficulty") if isinstance(message.get("difficulty"), str) else session.difficulty
                entries = [_asdict(e) for e in SCOREBOARD.top(difficulty=requested)]
                await ws.send_json({"type": "scores", "difficulty": requested, "entries": entries})
                continue

            # A new_game with a difficulty payload swaps the underlying Game
            # for one with the requested num_colors. Without a payload, the
            # existing Game is reused and just reset — keeps undo history
            # conventions matching the domain's new_game.
            if msg_type == "new_game" and isinstance(message.get("difficulty"), str):
                session.difficulty = message["difficulty"]
                game = _new_game(session.difficulty)
                session.game = game
                router = WebInput(game)
                presenter = WebPresenter()
                await ws.send_json(encode_snapshot(game))
                log_snapshot(sid, game)
                continue

            # Player-initiated end of the current session (e.g. confirmed
            # "Start New Game" while a game was in progress). Emits the
            # standard GameOver(won=False) so the scoreboard records the
            # result and the client shows its normal final-score overlay.
            if msg_type == "end_game":
                events = game.abandon()
                for event in events:
                    log_out(sid, event)
                    presenter.on_event(event)
                for frame in presenter.drain():
                    await ws.send_json(frame)
                for event in events:
                    if type(event).__name__ == "GameOver" and not getattr(event, "won", False):
                        SCOREBOARD.record(
                            name=session.name,
                            score=getattr(event, "score", 0),
                            level=getattr(event, "level", 1),
                            difficulty=session.difficulty,
                        )
                        break
                continue

            try:
                events = router.handle_message(message)
            except ValueError as exc:
                await ws.send_json({"type": "error", "message": str(exc)})
                continue

            for event in events:
                log_out(sid, event)
                presenter.on_event(event)
            for frame in presenter.drain():
                await ws.send_json(frame)

            # Record the final result when the session actually ends.
            for event in events:
                if type(event).__name__ == "GameOver" and not getattr(event, "won", False):
                    SCOREBOARD.record(
                        name=session.name,
                        score=getattr(event, "score", 0),
                        level=getattr(event, "level", 1),
                        difficulty=session.difficulty,
                    )
                    break

            # new_game resets state; undo restores an older state; LevelCleared
            # rebuilds the field for the next level. All three need a fresh
            # snapshot so the client repaints atomically — rebuilding from
            # events alone is error-prone across these transitions.
            type_names = {type(e).__name__ for e in events}
            if msg_type == "new_game" or "StateReverted" in type_names or "LevelCleared" in type_names:
                await ws.send_json(encode_snapshot(game))
                log_snapshot(sid, game)

    except WebSocketDisconnect:
        log_leave(sid)
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
