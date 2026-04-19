"""Shot rule: validates a launcher tap, activates the correct ammo brick, and
emits a BrickShot event. Invalid taps produce no events and don't mutate state.
"""

from domain.brick import Brick, CellIntention
from domain.constants import (
    FIELD_SIZE,
    LAUNCH_ZONE_DEPTH,
    PLAY_AREA_START,
    PLAY_AREA_END,
)
from domain.events import BrickShot
from domain.rules.shot import can_shoot, shoot


def empty_field() -> list[list[Brick]]:
    return [[Brick() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]


def place(field, r: int, c: int, color: int = 0, intention: CellIntention = CellIntention.STAND) -> None:
    field[r][c] = Brick(intention=intention, color_index=color)


# --- fully-loaded launcher row for right-shot scenarios --------------------
def setup_left_shot(field, row: int, color: int = 0) -> None:
    """Fill left launcher cells for `row` with ammo, put an obstacle in the path."""
    for c in range(LAUNCH_ZONE_DEPTH):
        place(field, row, c, color=color)
    place(field, row, PLAY_AREA_END - 1, color=color + 1)  # obstacle


class TestInvalidClicks:
    def test_click_inside_play_area_is_ignored(self):
        field = empty_field()
        events = shoot(field, (PLAY_AREA_START + 2, PLAY_AREA_START + 2))
        assert events == []

    def test_click_on_corner_is_ignored(self):
        """Corners are outside the launcher trigger rows/cols."""
        field = empty_field()
        events = shoot(field, (0, 0))
        assert events == []


class TestValidLeftShot:
    def test_emits_brick_shot_event_with_correct_payload(self):
        field = empty_field()
        row = PLAY_AREA_START + 2
        setup_left_shot(field, row)

        events = shoot(field, (row, PLAY_AREA_START - 1))

        assert len(events) == 1
        e = events[0]
        assert isinstance(e, BrickShot)
        assert e.launcher_cell == (row, PLAY_AREA_START - 1)
        assert e.direction == "TO_RIGHT"
        # Innermost ammo cell is at column LAUNCH_ZONE_DEPTH - 1.
        assert e.ammo_cell == (row, LAUNCH_ZONE_DEPTH - 1)

    def test_innermost_ammo_brick_gets_direction(self):
        field = empty_field()
        row = PLAY_AREA_START + 2
        setup_left_shot(field, row)

        shoot(field, (row, PLAY_AREA_START - 1))

        innermost = field[row][LAUNCH_ZONE_DEPTH - 1]
        assert innermost.intention == CellIntention.TO_RIGHT


class TestValidShotsOtherSides:
    def test_right_launcher_sets_to_left_on_innermost(self):
        field = empty_field()
        row = PLAY_AREA_START + 2
        for c in range(PLAY_AREA_END, FIELD_SIZE):
            place(field, row, c, color=0)
        place(field, row, PLAY_AREA_START, color=1)  # obstacle

        events = shoot(field, (row, PLAY_AREA_END))

        assert len(events) == 1
        assert events[0].direction == "TO_LEFT"
        assert field[row][PLAY_AREA_END].intention == CellIntention.TO_LEFT

    def test_top_launcher_sets_to_down(self):
        field = empty_field()
        col = PLAY_AREA_START + 2
        for r in range(LAUNCH_ZONE_DEPTH):
            place(field, r, col, color=0)
        place(field, PLAY_AREA_END - 1, col, color=1)

        events = shoot(field, (PLAY_AREA_START - 1, col))

        assert len(events) == 1
        assert events[0].direction == "TO_DOWN"
        assert field[LAUNCH_ZONE_DEPTH - 1][col].intention == CellIntention.TO_DOWN

    def test_bottom_launcher_sets_to_up(self):
        field = empty_field()
        col = PLAY_AREA_START + 2
        for r in range(PLAY_AREA_END, FIELD_SIZE):
            place(field, r, col, color=0)
        place(field, PLAY_AREA_START, col, color=1)

        events = shoot(field, (PLAY_AREA_END, col))

        assert len(events) == 1
        assert events[0].direction == "TO_UP"


class TestShotPreconditions:
    def test_target_edge_occupied_blocks_shot(self):
        field = empty_field()
        row = PLAY_AREA_START + 2
        for c in range(LAUNCH_ZONE_DEPTH):
            place(field, row, c, color=0)
        place(field, row, PLAY_AREA_START, color=9)  # target edge occupied

        assert shoot(field, (row, PLAY_AREA_START - 1)) == []

    def test_no_obstacle_in_path_blocks_shot(self):
        """Firing into an empty row/column is not allowed."""
        field = empty_field()
        row = PLAY_AREA_START + 2
        for c in range(LAUNCH_ZONE_DEPTH):
            place(field, row, c, color=0)
        # No obstacle inside the play area.

        assert shoot(field, (row, PLAY_AREA_START - 1)) == []

    def test_empty_launcher_blocks_shot(self):
        """No ammo → no shot."""
        field = empty_field()
        row = PLAY_AREA_START + 2
        place(field, row, PLAY_AREA_END - 1, color=1)  # obstacle only

        assert shoot(field, (row, PLAY_AREA_START - 1)) == []


class TestCanShoot:
    """can_shoot mirrors shoot's preconditions without mutating the field.
    Used by the game-over detector to ask 'is there any valid shot anywhere?'"""

    def test_returns_true_for_valid_shot(self):
        field = empty_field()
        row = PLAY_AREA_START + 2
        setup_left_shot(field, row)

        assert can_shoot(field, (row, PLAY_AREA_START - 1)) is True
        # Field unchanged.
        for c in range(LAUNCH_ZONE_DEPTH):
            assert field[row][c].intention == CellIntention.STAND

    def test_returns_false_when_target_edge_occupied(self):
        field = empty_field()
        row = PLAY_AREA_START + 2
        for c in range(LAUNCH_ZONE_DEPTH):
            place(field, row, c, color=0)
        place(field, row, PLAY_AREA_START, color=9)
        assert can_shoot(field, (row, PLAY_AREA_START - 1)) is False

    def test_returns_false_for_non_launcher_click(self):
        assert can_shoot(empty_field(), (0, 0)) is False
