"""Crosser rule.

A brick sitting on the inside edge of the play area with outward intention has
"crossed" the field. It gets pushed into the opposite launcher queue: existing
launcher bricks shift outward (the outermost one is discarded) and the crosser
lands in the innermost launcher cell with STAND intention. One BrickCrossed
event is emitted per brick that crossed.
"""

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, LAUNCH_ZONE_DEPTH, PLAY_AREA_START, PLAY_AREA_END
from domain.events import BrickCrossed, BrickMoved
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

        # Empty launcher: no shift events, just the BrickCrossed.
        cross_events = [e for e in events if isinstance(e, BrickCrossed)]
        assert len(cross_events) == 1
        e = cross_events[0]
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

        events = handle_board_crossers(field)

        # Field state.
        assert field[row][PLAY_AREA_END].color_index == 9    # crosser
        assert field[row][PLAY_AREA_END + 1].color_index == 1  # former innermost shifted
        assert field[row][PLAY_AREA_END + 2].color_index == 2  # former middle shifted

        # Events: BrickMoved for each shifted brick + BrickCrossed for the crosser.
        moves = [e for e in events if isinstance(e, BrickMoved)]
        crosses = [e for e in events if isinstance(e, BrickCrossed)]
        assert len(crosses) == 1
        assert crosses[0].to_cell == (row, PLAY_AREA_END)

        # A BrickMoved per populated cell that shifted; outermost was VOID so no
        # "destroyed" event in this case.
        move_tuples = {(e.from_cell, e.to_cell) for e in moves}
        assert ((row, PLAY_AREA_END), (row, PLAY_AREA_END + 1)) in move_tuples
        assert ((row, PLAY_AREA_END + 1), (row, PLAY_AREA_END + 2)) in move_tuples

    def test_full_launcher_queue_discards_outermost_brick(self):
        """When every launcher cell is already occupied, the outermost brick
        gets overwritten — no BrickMoved emitted for it, but the event stream
        must still carry the shifts that DID happen."""
        field = empty_field()
        row = PLAY_AREA_START + 1
        place(field, row, PLAY_AREA_END - 1, color=9, intention=CellIntention.TO_RIGHT)
        place(field, row, PLAY_AREA_END, color=1)
        place(field, row, PLAY_AREA_END + 1, color=2)
        place(field, row, PLAY_AREA_END + 2, color=3)  # outermost — will be lost

        events = handle_board_crossers(field)

        assert field[row][PLAY_AREA_END].color_index == 9
        assert field[row][PLAY_AREA_END + 1].color_index == 1
        assert field[row][PLAY_AREA_END + 2].color_index == 2

        moves = [e for e in events if isinstance(e, BrickMoved)]
        # Two shift events (middle->outer, innermost->middle).
        move_tuples = {(e.from_cell, e.to_cell) for e in moves}
        assert ((row, PLAY_AREA_END + 1), (row, PLAY_AREA_END + 2)) in move_tuples
        assert ((row, PLAY_AREA_END), (row, PLAY_AREA_END + 1)) in move_tuples

    def test_shift_events_precede_cross_event(self):
        """The crosser arrives last so the client can destroy the outermost
        sprite (via its move being overwritten) before the new sprite lands."""
        field = empty_field()
        row = PLAY_AREA_START + 1
        place(field, row, PLAY_AREA_END - 1, color=9, intention=CellIntention.TO_RIGHT)
        place(field, row, PLAY_AREA_END, color=1)

        events = handle_board_crossers(field)

        last = events[-1]
        assert isinstance(last, BrickCrossed)
        assert last.to_cell == (row, PLAY_AREA_END)


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
