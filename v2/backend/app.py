"""FastAPI app — serves the game over a WebSocket.

One `Game` instance per connected client, held in memory for the lifetime of
the socket. On connect the server sends a snapshot; every incoming
input-port message is answered with the resulting domain events. Unknown
messages produce an `{"type": "error"}` frame instead of closing the socket.
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from domain.game import Game

from .adapters.snapshot import encode_snapshot
from .adapters.web_input import WebInput
from .adapters.web_presenter import WebPresenter


app = FastAPI()


@app.websocket("/ws")
async def game_ws(ws: WebSocket) -> None:
    await ws.accept()
    game = Game()
    game.new_game()
    presenter = WebPresenter()
    router = WebInput(game)

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
