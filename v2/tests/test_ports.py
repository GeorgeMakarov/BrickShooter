"""GameInputPort / GamePresenterPort are typing.Protocol definitions — no
inheritance required. A duck-typed implementation that provides the right
methods satisfies isinstance() checks with runtime_checkable Protocols.
"""

from domain.events import DomainEvent
from domain.ports import GameInputPort, GamePresenterPort


class _FakeInput:
    def new_game(self) -> list[DomainEvent]:
        return []

    def shoot(self, cell):
        return []

    def undo(self) -> list[DomainEvent]:
        return []


class _FakePresenter:
    def __init__(self):
        self.received: list[DomainEvent] = []

    def on_event(self, event: DomainEvent) -> None:
        self.received.append(event)


def test_input_port_is_runtime_checkable():
    assert isinstance(_FakeInput(), GameInputPort)


def test_presenter_port_is_runtime_checkable():
    assert isinstance(_FakePresenter(), GamePresenterPort)


def test_object_missing_methods_is_not_an_input_port():
    class Partial:
        def new_game(self):
            return []

    assert not isinstance(Partial(), GameInputPort)
