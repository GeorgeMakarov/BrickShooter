"""WebPresenter — buffers DomainEvents as JSON frames for the websocket.

The game's use-case methods (`shoot`, `undo`, `new_game`) produce events
synchronously. The async WS handler calls the input-port method, then calls
`drain()` on this presenter and sends the resulting frames to the client in
order. Keeping emission synchronous here lets the domain stay unaware of
asyncio.
"""

from domain.events import DomainEvent

from .codec import to_json


class WebPresenter:
    def __init__(self) -> None:
        self._buffer: list[dict] = []

    def on_event(self, event: DomainEvent) -> None:
        self._buffer.append(to_json(event))

    def drain(self) -> list[dict]:
        """Return all buffered frames in order and clear the buffer."""
        frames, self._buffer = self._buffer, []
        return frames
