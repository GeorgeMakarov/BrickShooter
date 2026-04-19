"""WebInput — translates decoded websocket messages into GameInputPort calls.

Message schema:

    {"type": "shoot", "cell": [r, c]}
    {"type": "undo"}
    {"type": "new_game"}

Malformed or unknown messages raise ValueError; the WS handler catches and
either ignores the frame or closes the connection depending on policy.
"""

from domain.events import DomainEvent
from domain.ports import GameInputPort


class WebInput:
    def __init__(self, game: GameInputPort) -> None:
        self._game = game

    def handle_message(self, frame: dict) -> list[DomainEvent]:
        msg_type = frame.get("type")
        if msg_type is None:
            raise ValueError("message missing 'type' field")

        if msg_type == "shoot":
            cell = _parse_cell(frame.get("cell"))
            return self._game.shoot(cell)
        if msg_type == "undo":
            return self._game.undo()
        if msg_type == "new_game":
            return self._game.new_game()

        raise ValueError(f"unknown message type: {msg_type}")


def _parse_cell(value) -> tuple[int, int]:
    if value is None:
        raise ValueError("shoot message missing 'cell' field")
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("shoot 'cell' must be a two-element array")
    try:
        return (int(value[0]), int(value[1]))
    except (TypeError, ValueError) as exc:
        raise ValueError("shoot 'cell' coordinates must be integers") from exc
