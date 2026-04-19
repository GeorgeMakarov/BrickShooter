"""Crosser rule.

A brick sitting on the inside edge of the play area with outward intention is
about to leave the field. Instead, it crosses into the launcher queue on the
opposite side: existing launcher bricks shift outward (the outermost is
discarded) and the crosser takes the innermost slot with STAND intention.

One BrickCrossed event per crossing brick.
"""

from dataclasses import dataclass
from typing import Callable, Iterable

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, LAUNCH_ZONE_DEPTH, PLAY_AREA_START, PLAY_AREA_END
from domain.events import BrickCrossed

Field = list[list[Brick]]
Cell = tuple[int, int]


@dataclass(frozen=True)
class _EdgeCheck:
    direction: CellIntention         #!< intention that counts as "crossing" this edge
    source_cells: tuple[Cell, ...]   #!< inside-edge cells scanned for a crosser
    dest_queue_for: Callable[[Cell], tuple[Cell, ...]]
    #!< given a source cell, returns the destination launcher queue ordered
    #!< innermost -> outermost


def handle_board_crossers(field: Field) -> list[BrickCrossed]:
    events: list[BrickCrossed] = []
    for check in _build_edge_checks():
        for source in check.source_cells:
            event = _cross_if_applicable(field, source, check.direction, check.dest_queue_for(source))
            if event is not None:
                events.append(event)
    return events


def _cross_if_applicable(
    field: Field,
    source: Cell,
    direction: CellIntention,
    dest_queue: tuple[Cell, ...],
) -> BrickCrossed | None:
    sr, sc = source
    brick = field[sr][sc]
    if brick.intention != direction:
        return None

    # Shift launcher queue outward (last cell discarded).
    for i in range(len(dest_queue) - 1, 0, -1):
        r_dest, c_dest = dest_queue[i]
        r_prev, c_prev = dest_queue[i - 1]
        field[r_dest][c_dest] = field[r_prev][c_prev]

    # Place crosser in the innermost slot as STAND.
    innermost = dest_queue[0]
    field[innermost[0]][innermost[1]] = Brick(
        intention=CellIntention.STAND,
        color_index=brick.color_index,
    )
    field[sr][sc] = Brick()

    return BrickCrossed(from_cell=source, to_cell=innermost, color_index=brick.color_index)


def _build_edge_checks() -> Iterable[_EdgeCheck]:
    return (
        # top edge: TO_UP crossers
        _EdgeCheck(
            direction=CellIntention.TO_UP,
            source_cells=tuple((PLAY_AREA_START, c) for c in range(PLAY_AREA_START, PLAY_AREA_END)),
            dest_queue_for=lambda src: tuple((i, src[1]) for i in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)),
        ),
        # bottom edge: TO_DOWN
        _EdgeCheck(
            direction=CellIntention.TO_DOWN,
            source_cells=tuple((PLAY_AREA_END - 1, c) for c in range(PLAY_AREA_START, PLAY_AREA_END)),
            dest_queue_for=lambda src: tuple((i, src[1]) for i in range(PLAY_AREA_END, FIELD_SIZE)),
        ),
        # left edge: TO_LEFT
        _EdgeCheck(
            direction=CellIntention.TO_LEFT,
            source_cells=tuple((r, PLAY_AREA_START) for r in range(PLAY_AREA_START, PLAY_AREA_END)),
            dest_queue_for=lambda src: tuple((src[0], i) for i in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)),
        ),
        # right edge: TO_RIGHT
        _EdgeCheck(
            direction=CellIntention.TO_RIGHT,
            source_cells=tuple((r, PLAY_AREA_END - 1) for r in range(PLAY_AREA_START, PLAY_AREA_END)),
            dest_queue_for=lambda src: tuple((src[0], i) for i in range(PLAY_AREA_END, FIELD_SIZE)),
        ),
    )
