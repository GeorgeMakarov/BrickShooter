"""Crosser rule.

A brick sitting on the inside edge of the play area with outward intention is
about to leave the field. Instead, it crosses into the launcher queue on the
opposite side: existing launcher bricks shift outward (the outermost is
discarded) and the crosser takes the innermost slot with STAND intention.

Per cross event, emits:
  - one `BrickMoved` for each populated shifted brick (outer-first, so a
    client that destroys the destination sprite on overwrite handles the
    outermost's discard naturally)
  - one `BrickCrossed` for the new arrival in the innermost slot (emitted
    last so shifts animate before the new brick lands)
"""

from dataclasses import dataclass
from typing import Callable, Iterable

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, LAUNCH_ZONE_DEPTH, PLAY_AREA_START, PLAY_AREA_END
from domain.events import BrickCrossed, BrickMoved, DomainEvent

Field = list[list[Brick]]
Cell = tuple[int, int]


@dataclass(frozen=True)
class _EdgeCheck:
    direction: CellIntention         #!< intention that counts as "crossing" this edge
    source_cells: tuple[Cell, ...]   #!< inside-edge cells scanned for a crosser
    dest_queue_for: Callable[[Cell], tuple[Cell, ...]]
    #!< given a source cell, returns the destination launcher queue ordered
    #!< innermost -> outermost


def handle_board_crossers(field: Field) -> list[DomainEvent]:
    events: list[DomainEvent] = []
    for check in _build_edge_checks():
        for source in check.source_cells:
            events.extend(
                _cross_if_applicable(field, source, check.direction, check.dest_queue_for(source))
            )
    return events


def _cross_if_applicable(
    field: Field,
    source: Cell,
    direction: CellIntention,
    dest_queue: tuple[Cell, ...],
) -> list[DomainEvent]:
    sr, sc = source
    brick = field[sr][sc]
    if brick.intention != direction:
        return []

    events: list[DomainEvent] = []

    # Shift launcher queue outward (outermost cell overwritten, data lost).
    # Iterate outer-to-inner so each shift's destination is either empty or
    # being vacated in the same batch. Emit BrickMoved only when the source
    # is actually populated — VOID cells shifting are silent.
    for i in range(len(dest_queue) - 1, 0, -1):
        dst = dest_queue[i]
        src = dest_queue[i - 1]
        src_brick = field[src[0]][src[1]]
        if src_brick.intention != CellIntention.VOID:
            events.append(BrickMoved(from_cell=src, to_cell=dst))
        field[dst[0]][dst[1]] = src_brick

    # Place crosser in the innermost slot as STAND.
    innermost = dest_queue[0]
    field[innermost[0]][innermost[1]] = Brick(
        intention=CellIntention.STAND,
        color_index=brick.color_index,
    )
    field[sr][sc] = Brick()

    events.append(BrickCrossed(from_cell=source, to_cell=innermost, color_index=brick.color_index))
    return events


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
