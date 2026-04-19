"""Matching rule: finds groups of >=3 same-colour adjacent bricks in the play
area, removes them, and emits BrickMatched events describing what was cleared.

Behaviour mirrors v1 `GameModel.find_and_remove_groups` but returns events
instead of plain coordinate lists. Scoring formula is unchanged.
"""

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, PLAY_AREA_START, PLAY_AREA_END
from domain.events import BrickMatched
from domain.rules.matching import find_and_remove_groups


def empty_field() -> list[list[Brick]]:
    return [[Brick() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]


def place(field, r: int, c: int, color: int, intention: CellIntention = CellIntention.STAND) -> None:
    field[r][c] = Brick(intention=intention, color_index=color)


class TestNoMatches:
    def test_empty_field_produces_no_events(self):
        events, score = find_and_remove_groups(empty_field())
        assert events == []
        assert score == 0

    def test_pair_not_removed(self):
        field = empty_field()
        row = PLAY_AREA_START + 2
        place(field, row, PLAY_AREA_START, color=4)
        place(field, row, PLAY_AREA_START + 1, color=4)

        events, score = find_and_remove_groups(field)

        assert events == []
        assert score == 0
        # Field unchanged.
        assert field[row][PLAY_AREA_START].intention == CellIntention.STAND
        assert field[row][PLAY_AREA_START + 1].intention == CellIntention.STAND


class TestSingleGroup:
    def test_horizontal_triplet_emits_one_event_and_clears_cells(self):
        field = empty_field()
        row = PLAY_AREA_START + 2
        cells = [(row, PLAY_AREA_START + dc) for dc in range(3)]
        for r, c in cells:
            place(field, r, c, color=4)

        events, score = find_and_remove_groups(field)

        assert len(events) == 1
        matched = events[0]
        assert isinstance(matched, BrickMatched)
        assert set(matched.cells) == set(cells)
        assert matched.color_index == 4

        for r, c in cells:
            assert field[r][c].intention == CellIntention.VOID

        assert score > 0

    def test_vertical_triplet_detected(self):
        field = empty_field()
        col = PLAY_AREA_START + 3
        cells = [(PLAY_AREA_START + dr, col) for dr in range(3)]
        for r, c in cells:
            place(field, r, c, color=7)

        events, _ = find_and_remove_groups(field)

        assert len(events) == 1
        assert set(events[0].cells) == set(cells)
        assert events[0].color_index == 7

    def test_l_shape_group_is_one_event(self):
        """A single BFS-connected group, regardless of shape, yields one event."""
        field = empty_field()
        r, c = PLAY_AREA_START + 1, PLAY_AREA_START + 1
        cells = [(r, c), (r, c + 1), (r, c + 2), (r + 1, c), (r + 2, c)]
        for rr, cc in cells:
            place(field, rr, cc, color=2)

        events, _ = find_and_remove_groups(field)

        assert len(events) == 1
        assert set(events[0].cells) == set(cells)
        assert len(events[0].cells) == 5


class TestMultipleGroups:
    def test_two_separate_triplets_emit_two_events(self):
        field = empty_field()
        # Horizontal triplet of colour 4 at row 4.
        row_a = PLAY_AREA_START + 1
        cells_a = [(row_a, PLAY_AREA_START + dc) for dc in range(3)]
        for r, c in cells_a:
            place(field, r, c, color=4)
        # Horizontal triplet of colour 6 at row 7.
        row_b = PLAY_AREA_START + 5
        cells_b = [(row_b, PLAY_AREA_START + dc) for dc in range(3)]
        for r, c in cells_b:
            place(field, r, c, color=6)

        events, _ = find_and_remove_groups(field)

        assert len(events) == 2
        colors = {e.color_index for e in events}
        assert colors == {4, 6}


class TestScoring:
    def test_larger_group_scores_more_than_minimum(self):
        def run(n: int) -> int:
            field = empty_field()
            row = PLAY_AREA_START + 2
            for dc in range(n):
                place(field, row, PLAY_AREA_START + dc, color=3)
            _, score = find_and_remove_groups(field)
            return score

        assert run(5) > run(3)

    def test_score_is_positive_integer(self):
        field = empty_field()
        row = PLAY_AREA_START + 2
        for dc in range(3):
            place(field, row, PLAY_AREA_START + dc, color=3)

        _, score = find_and_remove_groups(field)

        assert isinstance(score, int)
        assert score > 0


class TestPlayAreaScope:
    def test_matches_only_in_play_area(self):
        """Bricks inside launcher zones are ignored even if they'd form a group."""
        field = empty_field()
        row = PLAY_AREA_START + 2
        place(field, row, PLAY_AREA_START - 2, color=4)  # launcher
        place(field, row, PLAY_AREA_START - 1, color=4)  # launcher
        place(field, row, PLAY_AREA_START, color=4)      # play area

        events, score = find_and_remove_groups(field)

        assert events == []
        assert score == 0

    def test_group_straddling_play_boundary_only_counts_play_cells(self):
        field = empty_field()
        row = PLAY_AREA_START + 2
        # Two in play, one in launcher — should NOT match as a triplet.
        place(field, row, PLAY_AREA_START - 1, color=4)
        place(field, row, PLAY_AREA_START, color=4)
        place(field, row, PLAY_AREA_START + 1, color=4)

        events, _ = find_and_remove_groups(field)

        assert events == []


class TestMinGroupSizeParameter:
    def test_custom_min_group_size_allows_pairs(self):
        field = empty_field()
        row = PLAY_AREA_START + 2
        for dc in range(2):
            place(field, row, PLAY_AREA_START + dc, color=4)

        events, _ = find_and_remove_groups(field, min_group_size=2)

        assert len(events) == 1
