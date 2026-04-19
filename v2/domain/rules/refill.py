"""Refill rule.

Each of the 40 launcher queues is scanned from inside to outside. On the first
VOID found, the outer bricks shift inward one cell to fill the gap and a fresh
STAND brick appears at the (now-empty) outermost cell. Randomness is injected
via the `pick_color` callable so the rule stays deterministic in tests.

Emits:
  - BrickMoved for each brick that actually shifted;
  - LaunchZoneRefilled for each queue that got a new outermost brick.
"""

from typing import Callable

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, LAUNCH_ZONE_DEPTH, PLAY_AREA_START, PLAY_AREA_END
from domain.events import BrickMoved, DomainEvent, LaunchZoneRefilled

Field = list[list[Brick]]
Cell = tuple[int, int]
PickColor = Callable[[], int]


def refill_launch_zones(field: Field, pick_color: PickColor) -> list[DomainEvent]:
    events: list[DomainEvent] = []
    for queue in _all_queues():
        events.extend(_refill_queue(field, queue, pick_color))
    return events


def _refill_queue(field: Field, queue: tuple[Cell, ...], pick_color: PickColor) -> list[DomainEvent]:
    events: list[DomainEvent] = []
    for i, (r, c) in enumerate(queue):
        if field[r][c].intention != CellIntention.VOID:
            continue

        # Shift outer bricks one cell inward.
        for j in range(i, len(queue) - 1):
            dst = queue[j]
            src = queue[j + 1]
            field[dst[0]][dst[1]] = field[src[0]][src[1]]
            if field[dst[0]][dst[1]].intention != CellIntention.VOID:
                events.append(BrickMoved(from_cell=src, to_cell=dst))

        # Fresh brick at the outermost slot.
        outermost = queue[-1]
        color = pick_color()
        field[outermost[0]][outermost[1]] = Brick(
            intention=CellIntention.STAND,
            color_index=color,
        )
        events.append(LaunchZoneRefilled(new_cell=outermost, color_index=color))
        return events  # at most one refill per queue per call
    return events


def _all_queues() -> list[tuple[Cell, ...]]:
    """Ordered innermost -> outermost per queue."""
    queues: list[tuple[Cell, ...]] = []
    # top queues (one per play column)
    for c in range(PLAY_AREA_START, PLAY_AREA_END):
        queues.append(tuple((r, c) for r in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)))
    # bottom queues
    for c in range(PLAY_AREA_START, PLAY_AREA_END):
        queues.append(tuple((r, c) for r in range(PLAY_AREA_END, FIELD_SIZE)))
    # left queues (one per play row)
    for r in range(PLAY_AREA_START, PLAY_AREA_END):
        queues.append(tuple((r, c) for c in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)))
    # right queues
    for r in range(PLAY_AREA_START, PLAY_AREA_END):
        queues.append(tuple((r, c) for c in range(PLAY_AREA_END, FIELD_SIZE)))
    return queues
