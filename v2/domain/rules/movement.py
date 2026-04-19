"""Movement resolution step.

Performs one pass of movement across the field: every brick with a directional
intention moves one cell in that direction if the target is VOID. A brick
inside the play area pointing outward stays in place — crossing over the
boundary is handled by a separate rule.

Returns one `BrickMoved` event per move that actually happened.
"""

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, PLAY_AREA_START, PLAY_AREA_END
from domain.events import BrickMoved

Field = list[list[Brick]]
Cell = tuple[int, int]

_DIRECTIONAL = {
    CellIntention.TO_LEFT,
    CellIntention.TO_RIGHT,
    CellIntention.TO_UP,
    CellIntention.TO_DOWN,
}


def movement_resolution_step(field: Field) -> list[BrickMoved]:
    """Advance all movable bricks by one cell. Returns the moves that occurred."""
    moves: dict[Cell, Cell] = {}  # dest -> source (first writer wins)

    for r in range(FIELD_SIZE):
        for c in range(FIELD_SIZE):
            brick = field[r][c]
            if brick.intention not in _DIRECTIONAL:
                continue

            dc, dr = brick.intention_vector  # [col, row]
            tr, tc = r + dr, c + dc

            src_in_play = _in_play_area(r, c)
            dest_in_play = _in_play_area(tr, tc)
            if src_in_play and not dest_in_play:
                continue  # crossing handled elsewhere

            if not (0 <= tr < FIELD_SIZE and 0 <= tc < FIELD_SIZE):
                continue
            if field[tr][tc].intention != CellIntention.VOID:
                continue

            dest = (tr, tc)
            if dest not in moves:
                moves[dest] = (r, c)

    if not moves:
        return []

    events: list[BrickMoved] = []
    for dest, source in moves.items():
        sr, sc = source
        dr, dc = dest
        field[dr][dc], field[sr][sc] = field[sr][sc], field[dr][dc]
        events.append(BrickMoved(from_cell=source, to_cell=dest))

    return events


def _in_play_area(r: int, c: int) -> bool:
    return PLAY_AREA_START <= r < PLAY_AREA_END and PLAY_AREA_START <= c < PLAY_AREA_END
