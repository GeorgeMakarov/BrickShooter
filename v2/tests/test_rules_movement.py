"""Movement resolution step.

One pass: every brick with directional intention that can move into a VOID
neighbour does so. Bricks inside the play area pointing outward stay put
(that case is handled by the separate crosser rule).

The rule returns one BrickMoved event per move that happened.
"""

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, PLAY_AREA_START, PLAY_AREA_END
from domain.events import BrickMoved
from domain.rules.movement import movement_resolution_step


def empty_field() -> list[list[Brick]]:
    return [[Brick() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]


def place(field, r: int, c: int, color: int = 0, intention: CellIntention = CellIntention.STAND) -> None:
    field[r][c] = Brick(intention=intention, color_index=color)


class TestNoMovement:
    def test_empty_field_no_events(self):
        assert movement_resolution_step(empty_field()) == []

    def test_stand_brick_does_not_move(self):
        field = empty_field()
        place(field, PLAY_AREA_START + 1, PLAY_AREA_START + 5, intention=CellIntention.STAND)
        assert movement_resolution_step(field) == []


class TestSingleMove:
    def test_to_left_moves_one_cell_and_emits_event(self):
        field = empty_field()
        row = PLAY_AREA_START + 1
        place(field, row, PLAY_AREA_START + 5, intention=CellIntention.TO_LEFT)

        events = movement_resolution_step(field)

        assert events == [BrickMoved(from_cell=(row, PLAY_AREA_START + 5), to_cell=(row, PLAY_AREA_START + 4))]
        assert field[row][PLAY_AREA_START + 4].intention == CellIntention.TO_LEFT
        assert field[row][PLAY_AREA_START + 5].intention == CellIntention.VOID

    def test_to_right_moves_one_cell(self):
        field = empty_field()
        row = PLAY_AREA_START + 1
        place(field, row, PLAY_AREA_START + 2, intention=CellIntention.TO_RIGHT)

        events = movement_resolution_step(field)

        assert events == [BrickMoved(from_cell=(row, PLAY_AREA_START + 2), to_cell=(row, PLAY_AREA_START + 3))]

    def test_to_down_moves_one_cell(self):
        field = empty_field()
        col = PLAY_AREA_START + 2
        place(field, PLAY_AREA_START + 1, col, intention=CellIntention.TO_DOWN)

        events = movement_resolution_step(field)

        assert events == [BrickMoved(from_cell=(PLAY_AREA_START + 1, col), to_cell=(PLAY_AREA_START + 2, col))]

    def test_to_up_moves_one_cell(self):
        field = empty_field()
        col = PLAY_AREA_START + 2
        place(field, PLAY_AREA_START + 3, col, intention=CellIntention.TO_UP)

        events = movement_resolution_step(field)

        assert events == [BrickMoved(from_cell=(PLAY_AREA_START + 3, col), to_cell=(PLAY_AREA_START + 2, col))]


class TestBlockedMovement:
    def test_brick_blocked_by_non_void_neighbour_does_not_move(self):
        field = empty_field()
        row = PLAY_AREA_START + 1
        place(field, row, PLAY_AREA_START + 5, intention=CellIntention.TO_LEFT)
        place(field, row, PLAY_AREA_START + 4, intention=CellIntention.STAND)

        assert movement_resolution_step(field) == []
        assert field[row][PLAY_AREA_START + 5].intention == CellIntention.TO_LEFT


class TestPlayAreaBoundary:
    def test_brick_in_play_area_does_not_exit_via_move(self):
        """Crossing out is a separate rule (crosser). The movement step leaves
        this brick in place."""
        field = empty_field()
        row = PLAY_AREA_START + 1
        place(field, row, PLAY_AREA_START, intention=CellIntention.TO_LEFT)

        assert movement_resolution_step(field) == []
        assert field[row][PLAY_AREA_START].intention == CellIntention.TO_LEFT

    def test_brick_entering_play_area_from_launcher_is_allowed(self):
        """The shot brick sits in a launcher cell with an inward intention; its
        target (play-area edge) is a legal destination."""
        field = empty_field()
        row = PLAY_AREA_START + 1
        place(field, row, PLAY_AREA_START - 1, intention=CellIntention.TO_RIGHT)

        events = movement_resolution_step(field)

        assert events == [BrickMoved(from_cell=(row, PLAY_AREA_START - 1), to_cell=(row, PLAY_AREA_START))]


class TestMultipleIndependentMoves:
    def test_two_separate_bricks_each_move(self):
        field = empty_field()
        place(field, PLAY_AREA_START + 1, PLAY_AREA_START + 5, intention=CellIntention.TO_LEFT)
        place(field, PLAY_AREA_START + 3, PLAY_AREA_START + 5, intention=CellIntention.TO_LEFT)

        events = movement_resolution_step(field)

        assert len(events) == 2
        destinations = {e.to_cell for e in events}
        assert destinations == {
            (PLAY_AREA_START + 1, PLAY_AREA_START + 4),
            (PLAY_AREA_START + 3, PLAY_AREA_START + 4),
        }
