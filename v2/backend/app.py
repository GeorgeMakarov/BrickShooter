"""FastAPI app — serves the game over a WebSocket.

Games are kept alive in an in-memory session dict keyed by a `sid` the client
stores in localStorage. On reconnect with the same sid the existing Game is
reused — field, score, undo history all survive an F5. Unknown or stale sids
produce a fresh Game. Server restart wipes everything (in-memory only);
acceptable for a hobby deploy.

On connect the server sends `{type: "session", id: sid}` so the client can
save it, followed by a snapshot. Unknown input messages produce an
`{type: "error"}` frame without closing the socket.
"""

import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from domain.game import Game

from .adapters.snapshot import encode_snapshot
from .adapters.web_input import WebInput
from .adapters.web_presenter import WebPresenter


app = FastAPI()

# Per-session Game instances. Survives WS reconnects; cleared on server restart.
SESSIONS: dict[str, Game] = {}


def _get_or_create_game(sid: str | None) -> tuple[str, Game, bool]:
    """Returns (sid, game, is_new). If sid is None or unknown, a fresh Game
    and a new sid are produced."""
    if sid is not None and sid in SESSIONS:
        return sid, SESSIONS[sid], False
    new_sid = uuid.uuid4().hex
    game = Game()
    game.new_game()
    SESSIONS[new_sid] = game
    return new_sid, game, True


@app.websocket("/ws")
async def game_ws(ws: WebSocket) -> None:
    await ws.accept()

    requested_sid = ws.query_params.get("sid")
    sid, game, _ = _get_or_create_game(requested_sid)
    presenter = WebPresenter()
    router = WebInput(game)

    await ws.send_json({"type": "session", "id": sid})
    await ws.send_json(encode_snapshot(game))

    try:
        while True:
            message = await ws.receive_json()
            msg_type = message.get("type") if isinstance(message, dict) else None

            # Protocol-level request for a full state dump. Not a game input.
            if msg_type == "snapshot":
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
