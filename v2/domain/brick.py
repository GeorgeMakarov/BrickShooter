"""Brick entity and cell-intention enum.

A brick carries an intention (stationary / directional / void) and an optional
palette index. Intentions are numeric enum values whose layout matches v1 so
range-based checks (e.g. `1 <= value <= 4` for "is directional") keep working.
"""

from dataclasses import dataclass
from enum import IntEnum
from typing import Optional


class CellIntention(IntEnum):
    VOID = 0
    TO_LEFT = 1
    TO_RIGHT = 2
    TO_UP = 3
    TO_DOWN = 4
    STAND = 5


_INTENTION_VECTORS: dict[CellIntention, list[int]] = {
    CellIntention.TO_LEFT:  [-1, 0],
    CellIntention.TO_RIGHT: [1,  0],
    CellIntention.TO_UP:    [0, -1],
    CellIntention.TO_DOWN:  [0,  1],
    CellIntention.STAND:    [0,  0],
    CellIntention.VOID:     [0,  0],
}


@dataclass
class Brick:
    intention: CellIntention = CellIntention.VOID
    color_index: Optional[int] = None

    @property
    def intention_vector(self) -> list[int]:
        """Unit [col, row] offset for this brick's intention.

        STAND and VOID produce [0, 0]; directional intentions produce the
        corresponding cardinal step.
        """
        return _INTENTION_VECTORS[self.intention]
