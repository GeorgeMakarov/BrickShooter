"""WebInput parses incoming websocket messages and dispatches them to the
GameInputPort. Messages are JSON-decoded dicts with a `type` discriminator:

  {"type": "shoot", "cell": [r, c]}
  {"type": "undo"}
  {"type": "new_game"}

Returns the event list produced by the input-port call so the caller can hand
those events to a presenter.
"""

import pytest

from backend.adapters.web_input import WebInput
from domain.events import BrickMoved, DomainEvent


class _Spy:
    """Minimal GameInputPort that records every call and returns scripted events."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self._new_game_events: list[DomainEvent] = []
        self._shoot_events: list[DomainEvent] = []
        self._undo_events: list[DomainEvent] = []

    def new_game(self) -> list[DomainEvent]:
        self.calls.append(("new_game",))
        return list(self._new_game_events)

    def shoot(self, cell):
        self.calls.append(("shoot", cell))
        return list(self._shoot_events)

    def undo(self) -> list[DomainEvent]:
        self.calls.append(("undo",))
        return list(self._undo_events)


class TestDispatch:
    def test_shoot_routes_cell_as_tuple(self):
        spy = _Spy()
        WebInput(spy).handle_message({"type": "shoot", "cell": [2, 5]})
        assert spy.calls == [("shoot", (2, 5))]

    def test_undo_calls_undo(self):
        spy = _Spy()
        WebInput(spy).handle_message({"type": "undo"})
        assert spy.calls == [("undo",)]

    def test_new_game_calls_new_game(self):
        spy = _Spy()
        WebInput(spy).handle_message({"type": "new_game"})
        assert spy.calls == [("new_game",)]


class TestReturnValue:
    def test_returns_events_from_game(self):
        spy = _Spy()
        spy._shoot_events = [BrickMoved(from_cell=(0, 0), to_cell=(0, 1))]
        events = WebInput(spy).handle_message({"type": "shoot", "cell": [0, 0]})
        assert events == [BrickMoved(from_cell=(0, 0), to_cell=(0, 1))]


class TestErrors:
    def test_missing_type_raises(self):
        with pytest.raises(ValueError, match="type"):
            WebInput(_Spy()).handle_message({"cell": [0, 0]})

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="unknown"):
            WebInput(_Spy()).handle_message({"type": "do_stuff"})

    def test_shoot_without_cell_raises(self):
        with pytest.raises(ValueError, match="cell"):
            WebInput(_Spy()).handle_message({"type": "shoot"})

    @pytest.mark.parametrize("cell", [[0], [0, 1, 2], "abc", {"r": 0, "c": 0}])
    def test_shoot_with_malformed_cell_raises(self, cell):
        with pytest.raises(ValueError, match="cell"):
            WebInput(_Spy()).handle_message({"type": "shoot", "cell": cell})
