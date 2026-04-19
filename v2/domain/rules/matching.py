"""Group-matching rule.

Scans the play area for BFS-connected groups of same-colour bricks, removes
any group of at least `min_group_size` bricks, and reports what was cleared
via `BrickMatched` events. The caller is responsible for translating the
returned score delta into a `ScoreChanged` event (the rule has no access to
the cumulative total).
"""

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, PLAY_AREA_START, PLAY_AREA_END
from domain.events import BrickMatched

Field = list[list[Brick]]
Cell = tuple[int, int]

_BASE_SCORE = 10  #!< points per brick in a minimum-size group


def find_and_remove_groups(
    field: Field,
    min_group_size: int = 3,
) -> tuple[list[BrickMatched], int]:
    """Remove matching groups from `field` in place.

    Returns a list of `BrickMatched` events (one per removed group) and the
    total score earned this step.
    """
    events: list[BrickMatched] = []
    score = 0
    visited = [[False] * FIELD_SIZE for _ in range(FIELD_SIZE)]

    for r in range(PLAY_AREA_START, PLAY_AREA_END):
        for c in range(PLAY_AREA_START, PLAY_AREA_END):
            if visited[r][c]:
                continue
            brick = field[r][c]
            if brick.intention == CellIntention.VOID or brick.color_index is None:
                visited[r][c] = True
                continue

            group = _find_group(field, r, c, brick.color_index, visited)
            if len(group) < min_group_size:
                continue

            events.append(
                BrickMatched(cells=tuple(group), color_index=brick.color_index)
            )
            score += _score_for_group(len(group), min_group_size)
            for gr, gc in group:
                field[gr][gc] = Brick()

    return events, score


def _find_group(
    field: Field,
    start_r: int,
    start_c: int,
    color_index: int,
    visited: list[list[bool]],
) -> list[Cell]:
    """BFS inside the play area along same-colour edges."""
    queue: list[Cell] = [(start_r, start_c)]
    group: list[Cell] = []
    visited[start_r][start_c] = True

    while queue:
        r, c = queue.pop(0)
        group.append((r, c))
        for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
            nr, nc = r + dr, c + dc
            if not (PLAY_AREA_START <= nr < PLAY_AREA_END and PLAY_AREA_START <= nc < PLAY_AREA_END):
                continue
            if visited[nr][nc]:
                continue
            neighbour = field[nr][nc]
            if neighbour.intention == CellIntention.VOID or neighbour.color_index != color_index:
                continue
            visited[nr][nc] = True
            queue.append((nr, nc))

    return group


def _score_for_group(group_size: int, min_group_size: int) -> int:
    """Reward bigger groups more than the minimum."""
    bonus_multiplier = (group_size - min_group_size) + 1
    return group_size * _BASE_SCORE * bonus_multiplier
