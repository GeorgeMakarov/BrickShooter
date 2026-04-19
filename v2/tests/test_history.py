"""HistoryStack.

A bounded LIFO of (field, score) snapshots. `save` deep-copies the field so
subsequent mutations don't leak into stored states. `revert` pops the top
snapshot and emits a StateReverted event.
"""

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE
from domain.events import StateReverted
from domain.history import HistoryStack, Snapshot


def small_field(color: int = 0) -> list[list[Brick]]:
    field = [[Brick() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]
    field[5][5] = Brick(intention=CellIntention.STAND, color_index=color)
    return field


class TestEmptyHistory:
    def test_depth_is_zero(self):
        assert HistoryStack().depth == 0

    def test_revert_on_empty_returns_nothing(self):
        events, snap = HistoryStack().revert()
        assert events == []
        assert snap is None


class TestSaveAndRevert:
    def test_save_increments_depth(self):
        h = HistoryStack()
        h.save(small_field(), score=0)
        assert h.depth == 1
        h.save(small_field(), score=10)
        assert h.depth == 2

    def test_revert_returns_most_recent_snapshot(self):
        h = HistoryStack()
        h.save(small_field(color=1), score=1)
        h.save(small_field(color=2), score=2)

        events, snap = h.revert()

        assert snap is not None
        assert snap.score == 2
        assert snap.field[5][5].color_index == 2
        assert h.depth == 1

    def test_revert_emits_state_reverted_event(self):
        h = HistoryStack()
        h.save(small_field(), score=42)

        events, _ = h.revert()

        assert events == [StateReverted(score=42)]


class TestDeepCopy:
    def test_mutating_field_after_save_does_not_affect_snapshot(self):
        h = HistoryStack()
        field = small_field(color=7)
        h.save(field, score=0)

        field[5][5].color_index = 99  # mutate after save

        _, snap = h.revert()
        assert snap is not None
        assert snap.field[5][5].color_index == 7

    def test_snapshot_field_independent_of_original_list(self):
        h = HistoryStack()
        field = small_field(color=4)
        h.save(field, score=0)

        # Replace a cell in the live field.
        field[5][5] = Brick()

        _, snap = h.revert()
        assert snap is not None
        assert snap.field[5][5].intention == CellIntention.STAND
        assert snap.field[5][5].color_index == 4


class TestSnapshot:
    def test_snapshot_exposes_field_and_score(self):
        snap = Snapshot(field=small_field(color=1), score=50)
        assert snap.score == 50
        assert snap.field[5][5].color_index == 1
