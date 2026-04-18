"""Tests for the Brick entity and CellIntention enum.

Mirrors the implicit contract used by v1: Brick is a plain data container
with an intention and an optional color_index; intention_vector yields the
unit movement vector for the enum variant.
"""

import pytest

from domain.brick import Brick, CellIntention


class TestCellIntention:
    def test_values_match_v1_numeric_ordering(self):
        # v1/model.py uses intention.value in range(1, 5) to detect directional
        # intent. Keep the same numeric layout so any logic ported from v1 keeps
        # working without rewrites.
        assert CellIntention.VOID.value == 0
        assert CellIntention.TO_LEFT.value == 1
        assert CellIntention.TO_RIGHT.value == 2
        assert CellIntention.TO_UP.value == 3
        assert CellIntention.TO_DOWN.value == 4
        assert CellIntention.STAND.value == 5


class TestBrickDefaults:
    def test_default_brick_is_void_with_no_color(self):
        b = Brick()
        assert b.intention == CellIntention.VOID
        assert b.color_index is None

    def test_construct_with_intention_and_color(self):
        b = Brick(intention=CellIntention.STAND, color_index=3)
        assert b.intention == CellIntention.STAND
        assert b.color_index == 3


class TestIntentionVector:
    @pytest.mark.parametrize(
        "intention, expected",
        [
            (CellIntention.TO_LEFT,  [-1, 0]),
            (CellIntention.TO_RIGHT, [1,  0]),
            (CellIntention.TO_UP,    [0, -1]),
            (CellIntention.TO_DOWN,  [0,  1]),
            (CellIntention.STAND,    [0,  0]),
            (CellIntention.VOID,     [0,  0]),
        ],
    )
    def test_intention_vector_matches_v1(self, intention, expected):
        assert Brick(intention=intention).intention_vector == expected
