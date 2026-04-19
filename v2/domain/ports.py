"""Port interfaces for the domain.

GameInputPort is what adapters call into: taps, button presses, WS messages
etc. all translate to these three methods.

GamePresenterPort is the sink events are pushed to. Every rendering/transport
adapter implements it: Kivy view, WebSocket encoder, local logger, fake test
double. One method keeps the contract trivial.

Both are typing.Protocol with @runtime_checkable so adapters can duck-type
without an inheritance bond.
"""

from typing import Protocol, runtime_checkable

from domain.events import DomainEvent


Cell = tuple[int, int]


@runtime_checkable
class GameInputPort(Protocol):
    def new_game(self) -> list[DomainEvent]: ...
    def shoot(self, cell: Cell) -> list[DomainEvent]: ...
    def undo(self) -> list[DomainEvent]: ...


@runtime_checkable
class GamePresenterPort(Protocol):
    def on_event(self, event: DomainEvent) -> None: ...
