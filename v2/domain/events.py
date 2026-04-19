"""Domain events emitted by the game engine.

Each event is an immutable value that describes one thing that happened to the
game state. Rendering adapters (Kivy, Godot, browser, ...) subscribe via the
presenter port and translate events to their native animation/sound calls.

Frozen dataclasses are used so events can be hashed, compared by value, and
safely fanned out to multiple subscribers without defensive copies.
"""

from dataclasses import dataclass


Cell = tuple[int, int]


@dataclass(frozen=True)
class DomainEvent:
    """Base tag for every event. Concrete events subclass this."""


@dataclass(frozen=True)
class BrickShot(DomainEvent):
    """A player action set directional intention on an ammo brick."""

    launcher_cell: Cell      #!< the cell the player tapped
    ammo_cell: Cell          #!< the launcher cell whose brick was activated
    direction: str           #!< "TO_LEFT" / "TO_RIGHT" / "TO_UP" / "TO_DOWN"


@dataclass(frozen=True)
class BrickMoved(DomainEvent):
    """A brick moved exactly one cell during a resolution step."""

    from_cell: Cell
    to_cell: Cell


@dataclass(frozen=True)
class BrickMatched(DomainEvent):
    """A group of same-colour bricks was matched and removed."""

    cells: tuple[Cell, ...]
    color_index: int


@dataclass(frozen=True)
class BrickCrossed(DomainEvent):
    """A moving brick crossed the play-area boundary into a launcher queue."""

    from_cell: Cell
    to_cell: Cell
    color_index: int


@dataclass(frozen=True)
class LaunchZoneRefilled(DomainEvent):
    """A launcher queue shifted inward and a fresh brick was added at the far end."""

    new_cell: Cell
    color_index: int


@dataclass(frozen=True)
class ScoreChanged(DomainEvent):
    delta: int
    total: int


@dataclass(frozen=True)
class StateReverted(DomainEvent):
    """An undo rolled state back by one shot. Payload is the restored score;
    presenters should re-query the field to repaint atomically."""

    score: int


@dataclass(frozen=True)
class LevelCleared(DomainEvent):
    """Play area emptied — session continues at the next level with the same
    score. Payload is the level that was just cleared."""

    level: int


@dataclass(frozen=True)
class GameOver(DomainEvent):
    reason: str
    won: bool
    level: int = 1
    score: int = 0
