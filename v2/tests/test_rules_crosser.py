"""Crosser rule.

A brick sitting on the inside edge of the play area with outward intention has
"crossed" the field. It gets pushed into the opposite launcher queue: existing
launcher bricks shift outward (the outermost one is discarded) and the crosser
lands in the innermost launcher cell with STAND intention. One BrickCrossed
event is emitted per brick that crossed.
"""

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, LAUNCH_ZONE_DEPTH, PLAY_AREA_START, PLAY_AREA_END
from domain.events import BrickCrossed
from domain.rules.crosser import handle_board_crossers


def empty_field() -> list[list[Brick]]:
    return [[Brick() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]


def place(field, r: int, c: int, color: int = 0, intention: CellIntention = CellIntention.STAND) -> None:
    field[r][c] = Brick(intention=intention, color_index=color)


class TestNoCrossers:
    def test_empty_field_no_events(self):
        assert handle_board_crossers(empty_field()) == []

    def test_non_crossing_brick_ignored(self):
        field = empty_field()
        place(field, PLAY_AREA_START + 1, PLAY_AREA_START + 5, color=3, intention=CellIntention.TO_RIGHT)
        assert handle_board_crossers(field) == []

    def test_brick_at_wrong_edge_not_a_crosser(self):
        """A TO_RIGHT brick on the LEFT edge is not crossing anything."""
        field = empty_field()
        place(field, PLAY_AREA_START + 1, PLAY_AREA_START, color=3, intention=CellIntention.TO_RIGHT)
        assert handle_board_crossers(field) == []


class TestRightEdgeCrosser:
    def test_brick_with_to_right_at_right_edge_crosses_into_launcher(self):
        field = empty_field()
        row = PLAY_AREA_START + 1
        place(field, row, PLAY_AREA_END - 1, color=3, intention=CellIntention.TO_RIGHT)

        events = handle_board_crossers(field)

        assert len(events) == 1
        e = events[0]
        assert isinstance(e, BrickCrossed)
        assert e.from_cell == (row, PLAY_AREA_END - 1)
        assert e.to_cell == (row, PLAY_AREA_END)  # innermost right-launcher cell
        assert e.color_index == 3

        landed = field[row][PLAY_AREA_END]
        assert landed.intention == CellIntention.STAND
        assert landed.color_index == 3

        assert field[row][PLAY_AREA_END - 1].intention == CellIntention.VOID

    def test_existing_launcher_bricks_shift_outward(self):
        field = empty_field()
        row = PLAY_AREA_START + 1
        place(field, row, PLAY_AREA_END - 1, color=9, intention=CellIntention.TO_RIGHT)
        # Prime the launcher queue with three distinctly coloured bricks.
        place(field, row, PLAY_AREA_END, color=1)
        place(field, row, PLAY_AREA_END + 1, color=2)
        # PLAY_AREA_END + 2 is the outermost cell, left VOID so the shift has room.

        handle_board_crossers(field)

        # Innermost launcher cell has the crosser's colour.
        assert field[row][PLAY_AREA_END].color_index == 9
        # Former innermost (colour 1) shifted one cell outward.
        assert field[row][PLAY_AREA_END + 1].color_index == 1
        # Former middle (colour 2) shifted to the outermost slot.
        assert field[row][PLAY_AREA_END + 2].color_index == 2


class TestAllFourSides:
    def test_left_edge_crosser(self):
        field = empty_field()
        row = PLAY_AREA_START + 2
        place(field, row, PLAY_AREA_START, color=5, intention=CellIntention.TO_LEFT)

        events = handle_board_crossers(field)

        assert len(events) == 1
        assert events[0].to_cell == (row, LAUNCH_ZONE_DEPTH - 1)  # innermost left launcher
        assert field[row][LAUNCH_ZONE_DEPTH - 1].intention == CellIntention.STAND

    def test_top_edge_crosser(self):
        field = empty_field()
        col = PLAY_AREA_START + 2
        place(field, PLAY_AREA_START, col, color=5, intention=CellIntention.TO_UP)

        events = handle_board_crossers(field)

        assert len(events) == 1
        assert events[0].to_cell == (LAUNCH_ZONE_DEPTH - 1, col)

    def test_bottom_edge_crosser(self):
        field = empty_field()
        col = PLAY_AREA_START + 2
        place(field, PLAY_AREA_END - 1, col, color=5, intention=CellIntention.TO_DOWN)

        events = handle_board_crossers(field)

        assert len(events) == 1
        assert events[0].to_cell == (PLAY_AREA_END, col)
