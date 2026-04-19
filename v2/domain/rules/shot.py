"""Shot rule.

A player tap on one of the four launcher strips (row/col just outside the
play area) triggers a shot, provided:
  1. the play-area cell adjacent to the tap is VOID,
  2. there is at least one non-VOID brick somewhere along the shot's path
     within the play area (you can't shoot into an empty line),
  3. the launcher queue contains at least one ammo brick.

When all preconditions hold, the innermost ammo brick gets a directional
intention pointing into the play area and a single BrickShot event is emitted.
"""

from dataclasses import dataclass
from typing import Optional

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, LAUNCH_ZONE_DEPTH, PLAY_AREA_START, PLAY_AREA_END
from domain.events import BrickShot

Field = list[list[Brick]]
Cell = tuple[int, int]


@dataclass(frozen=True)
class _ShotGeometry:
    target_cell: Cell                #!< play-area edge cell that must be VOID
    direction: CellIntention         #!< intention placed on the ammo brick
    direction_name: str              #!< human-readable form used in the event
    ammo_cells: tuple[Cell, ...]     #!< ordered inner -> outer
    path_cells: tuple[Cell, ...]     #!< play-area cells scanned for an obstacle


def shoot(field: Field, click_cell: Cell) -> list[BrickShot]:
    """Fire a shot from the tapped launcher cell. Mutates `field` on success."""
    geometry = _launcher_geometry(*click_cell)
    if geometry is None:
        return []

    if field[geometry.target_cell[0]][geometry.target_cell[1]].intention != CellIntention.VOID:
        return []

    if not _has_obstacle(field, geometry.path_cells):
        return []

    ammo_cell = _innermost_ammo(field, geometry.ammo_cells)
    if ammo_cell is None:
        return []

    field[ammo_cell[0]][ammo_cell[1]].intention = geometry.direction
    return [BrickShot(launcher_cell=click_cell, ammo_cell=ammo_cell, direction=geometry.direction_name)]


def _launcher_geometry(r: int, c: int) -> Optional[_ShotGeometry]:
    """Map a tap coordinate to the corresponding launcher's geometry, or None."""
    in_play_rows = PLAY_AREA_START <= r < PLAY_AREA_END
    in_play_cols = PLAY_AREA_START <= c < PLAY_AREA_END

    if c == PLAY_AREA_START - 1 and in_play_rows:  # left launcher strip
        return _ShotGeometry(
            target_cell=(r, PLAY_AREA_START),
            direction=CellIntention.TO_RIGHT,
            direction_name="TO_RIGHT",
            ammo_cells=tuple((r, i) for i in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)),
            path_cells=tuple((r, i) for i in range(PLAY_AREA_START + 1, PLAY_AREA_END)),
        )
    if c == PLAY_AREA_END and in_play_rows:  # right launcher strip
        return _ShotGeometry(
            target_cell=(r, PLAY_AREA_END - 1),
            direction=CellIntention.TO_LEFT,
            direction_name="TO_LEFT",
            ammo_cells=tuple((r, i) for i in range(PLAY_AREA_END, FIELD_SIZE)),
            path_cells=tuple((r, i) for i in range(PLAY_AREA_END - 2, PLAY_AREA_START - 1, -1)),
        )
    if r == PLAY_AREA_START - 1 and in_play_cols:  # top launcher strip
        return _ShotGeometry(
            target_cell=(PLAY_AREA_START, c),
            direction=CellIntention.TO_DOWN,
            direction_name="TO_DOWN",
            ammo_cells=tuple((i, c) for i in range(LAUNCH_ZONE_DEPTH - 1, -1, -1)),
            path_cells=tuple((i, c) for i in range(PLAY_AREA_START + 1, PLAY_AREA_END)),
        )
    if r == PLAY_AREA_END and in_play_cols:  # bottom launcher strip
        return _ShotGeometry(
            target_cell=(PLAY_AREA_END - 1, c),
            direction=CellIntention.TO_UP,
            direction_name="TO_UP",
            ammo_cells=tuple((i, c) for i in range(PLAY_AREA_END, FIELD_SIZE)),
            path_cells=tuple((i, c) for i in range(PLAY_AREA_END - 2, PLAY_AREA_START - 1, -1)),
        )
    return None


def _has_obstacle(field: Field, path: tuple[Cell, ...]) -> bool:
    return any(field[r][c].intention != CellIntention.VOID for r, c in path)


def _innermost_ammo(field: Field, ammo: tuple[Cell, ...]) -> Optional[Cell]:
    for r, c in ammo:
        if field[r][c].intention != CellIntention.VOID:
            return (r, c)
    return None
