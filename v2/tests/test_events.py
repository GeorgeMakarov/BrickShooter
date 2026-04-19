"""Construction and payload tests for DomainEvent variants.

These pin the event contract the presenter port will consume. Events must be
immutable (frozen dataclasses) so adapters can fan out the stream without
worrying about mutation.
"""

from dataclasses import FrozenInstanceError

import pytest

from domain.events import (
    BrickCrossed,
    BrickMatched,
    BrickMoved,
    BrickShot,
    DomainEvent,
    GameOver,
    LaunchZoneRefilled,
    LevelCleared,
    ScoreChanged,
    StateReverted,
)


class TestBrickShot:
    def test_payload(self):
        e = BrickShot(launcher_cell=(5, 2), ammo_cell=(5, 2), direction="TO_RIGHT")
        assert e.launcher_cell == (5, 2)
        assert e.ammo_cell == (5, 2)
        assert e.direction == "TO_RIGHT"

    def test_is_domain_event(self):
        assert isinstance(BrickShot(launcher_cell=(0, 0), ammo_cell=(0, 0), direction="TO_LEFT"), DomainEvent)


class TestBrickMoved:
    def test_payload(self):
        e = BrickMoved(from_cell=(5, 13), to_cell=(5, 12))
        assert e.from_cell == (5, 13)
        assert e.to_cell == (5, 12)

    def test_is_domain_event(self):
        assert isinstance(BrickMoved(from_cell=(0, 0), to_cell=(0, 1)), DomainEvent)


class TestBrickMatched:
    def test_payload(self):
        cells = ((5, 3), (5, 4), (5, 5))
        e = BrickMatched(cells=cells, color_index=2)
        assert e.cells == cells
        assert e.color_index == 2

    def test_cells_are_tuples_not_lists(self):
        e = BrickMatched(cells=((5, 3), (5, 4), (5, 5)), color_index=2)
        assert isinstance(e.cells, tuple)


class TestBrickCrossed:
    def test_payload(self):
        e = BrickCrossed(from_cell=(5, 12), to_cell=(5, 13), color_index=4)
        assert e.from_cell == (5, 12)
        assert e.to_cell == (5, 13)
        assert e.color_index == 4


class TestLaunchZoneRefilled:
    def test_payload(self):
        e = LaunchZoneRefilled(new_cell=(5, 15), color_index=7)
        assert e.new_cell == (5, 15)
        assert e.color_index == 7


class TestScoreChanged:
    def test_payload(self):
        e = ScoreChanged(delta=30, total=130)
        assert e.delta == 30
        assert e.total == 130


class TestStateReverted:
    def test_payload(self):
        e = StateReverted(score=42)
        assert e.score == 42


class TestLevelCleared:
    def test_payload(self):
        e = LevelCleared(level=3)
        assert e.level == 3


class TestGameOver:
    def test_loss_with_score_and_level(self):
        e = GameOver(reason="No moves", won=False, level=4, score=120)
        assert e.won is False
        assert e.level == 4
        assert e.score == 120

    def test_legacy_defaults(self):
        """Older call sites without level/score still work."""
        e = GameOver(reason="x", won=False)
        assert e.level == 1
        assert e.score == 0


class TestImmutability:
    def test_events_are_frozen(self):
        e = BrickMoved(from_cell=(0, 0), to_cell=(0, 1))
        with pytest.raises(FrozenInstanceError):
            e.to_cell = (9, 9)  # type: ignore[misc]

    def test_events_are_equal_by_value(self):
        assert BrickMoved(from_cell=(0, 0), to_cell=(0, 1)) == BrickMoved(from_cell=(0, 0), to_cell=(0, 1))

    def test_events_are_hashable(self):
        {BrickMoved(from_cell=(0, 0), to_cell=(0, 1))}  # does not raise
