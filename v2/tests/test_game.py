"""Game facade — the single entry point the input adapter talks to.

Responsibilities:
  - own the field, score, history
  - orchestrate the resolution cycle (movement → crossers → match → refill,
    repeated until stable)
  - emit ScoreChanged after every match batch
  - emit GameOver at the end of a cycle if applicable
  - expose new_game / shoot / undo as event-returning use cases
"""

import itertools

import pytest

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, LAUNCH_ZONE_DEPTH, PLAY_AREA_START, PLAY_AREA_END
from domain.events import (
    BrickCrossed,
    BrickMatched,
    BrickMoved,
    BrickShot,
    GameOver,
    LaunchZoneRefilled,
    ScoreChanged,
    StateReverted,
)
from domain.game import Game


# --- helpers -----------------------------------------------------------


def empty_game(color_seq=None) -> Game:
    """Game with a deterministic colour source and no default obstacles, so
    tests own the play-area contents. Tests that need v1's default obstacle
    placement construct `Game(num_obstacles=2)` explicitly."""
    if color_seq is None:
        color_seq = itertools.cycle([0])
    it = iter(color_seq)
    return Game(pick_color=lambda: next(it), num_obstacles=0)


def place(g: Game, r: int, c: int, color: int = 0, intention: CellIntention = CellIntention.STAND) -> None:
    g.field[r][c] = Brick(intention=intention, color_index=color)


# --- new_game ----------------------------------------------------------


class TestNewGame:
    def test_score_reset_to_zero(self):
        g = empty_game()
        g.score = 123
        g.new_game()
        assert g.score == 0

    def test_history_cleared(self):
        g = empty_game()
        g.history.save(g.field, 0)
        g.new_game()
        assert g.history.depth == 0

    def test_launchers_are_populated(self):
        g = empty_game()
        g.new_game()
        # Every launcher cell (outside play area) should now hold a STAND brick.
        for r in range(PLAY_AREA_START, PLAY_AREA_END):
            for c in range(LAUNCH_ZONE_DEPTH):                     # left
                assert g.field[r][c].intention == CellIntention.STAND
            for c in range(PLAY_AREA_END, FIELD_SIZE):             # right
                assert g.field[r][c].intention == CellIntention.STAND

    def test_play_area_gets_default_obstacles(self):
        """v1 parity: new_game places 2 random STAND obstacles inside the play
        area so the very first shot has something to aim at. Without this the
        game is unplayable (every shot rejected by the 'obstacle in path'
        precondition)."""
        g = Game(pick_color=lambda: 0)
        g.new_game()
        play_area_bricks = [
            g.field[r][c]
            for r in range(PLAY_AREA_START, PLAY_AREA_END)
            for c in range(PLAY_AREA_START, PLAY_AREA_END)
            if g.field[r][c].intention == CellIntention.STAND
        ]
        assert len(play_area_bricks) == 2

    def test_num_obstacles_parameter_controls_count(self):
        g = Game(pick_color=lambda: 0, num_obstacles=5)
        g.new_game()
        play_area_bricks = [
            g.field[r][c]
            for r in range(PLAY_AREA_START, PLAY_AREA_END)
            for c in range(PLAY_AREA_START, PLAY_AREA_END)
            if g.field[r][c].intention == CellIntention.STAND
        ]
        assert len(play_area_bricks) == 5

    def test_zero_obstacles_leaves_play_area_empty(self):
        g = Game(pick_color=lambda: 0, num_obstacles=0)
        g.new_game()
        for r in range(PLAY_AREA_START, PLAY_AREA_END):
            for c in range(PLAY_AREA_START, PLAY_AREA_END):
                assert g.field[r][c].intention == CellIntention.VOID


# --- shoot -------------------------------------------------------------


class TestShootInvalid:
    def test_invalid_click_returns_empty_and_leaves_history_untouched(self):
        g = empty_game()
        g.new_game()
        depth_before = g.history.depth

        events = g.shoot((PLAY_AREA_START + 2, PLAY_AREA_START + 2))  # inside play area

        assert events == []
        assert g.history.depth == depth_before


class TestShootValid:
    def test_first_event_is_brick_shot(self):
        g = empty_game()
        g.new_game()
        # A shot will fail unless there's an obstacle; place one.
        row = PLAY_AREA_START + 2
        place(g, row, PLAY_AREA_END - 1, color=9)

        events = g.shoot((row, PLAY_AREA_START - 1))

        assert events, "expected at least one event"
        assert isinstance(events[0], BrickShot)

    def test_history_recorded(self):
        g = empty_game()
        g.new_game()
        row = PLAY_AREA_START + 2
        place(g, row, PLAY_AREA_END - 1, color=9)

        g.shoot((row, PLAY_AREA_START - 1))

        assert g.history.depth == 1

    def test_cycle_produces_move_events_and_refill(self):
        """After the shot, resolution loops: BrickMoved for each cell the ammo
        traverses, then refill fires for the now-empty inner launcher slot."""
        g = empty_game()
        g.new_game()
        row = PLAY_AREA_START + 2
        place(g, row, PLAY_AREA_END - 1, color=9)

        events = g.shoot((row, PLAY_AREA_START - 1))

        assert any(isinstance(e, BrickMoved) for e in events)
        assert any(isinstance(e, LaunchZoneRefilled) for e in events)


class TestShootWithMatch:
    def test_match_produces_brick_matched_and_score_changed(self):
        """Arrange two bricks of colour 7 in a row; the shot brick also colour 7
        completes a triplet, triggers BrickMatched and ScoreChanged."""
        # Deterministic colours: every new launcher brick is colour 7.
        g = Game(pick_color=lambda: 7, num_obstacles=0)
        g.new_game()
        row = PLAY_AREA_START + 2
        # Two existing colour-7 bricks in the row, plus an obstacle further in.
        place(g, row, PLAY_AREA_START + 1, color=7)
        place(g, row, PLAY_AREA_START + 2, color=7)
        place(g, row, PLAY_AREA_END - 1, color=9)  # obstacle so shot fires

        events = g.shoot((row, PLAY_AREA_START - 1))

        matches = [e for e in events if isinstance(e, BrickMatched)]
        score_changes = [e for e in events if isinstance(e, ScoreChanged)]
        assert matches, "expected at least one match event"
        assert score_changes, "expected ScoreChanged to follow the match"
        assert score_changes[0].total == g.score
        assert g.score > 0


# --- undo --------------------------------------------------------------


class TestUndo:
    def test_undo_without_history_returns_empty(self):
        g = empty_game()
        assert g.undo() == []

    def test_undo_emits_state_reverted_and_restores_score(self):
        g = empty_game()
        g.new_game()
        row = PLAY_AREA_START + 2
        place(g, row, PLAY_AREA_END - 1, color=9)
        pre_score = g.score

        g.shoot((row, PLAY_AREA_START - 1))
        assert g.history.depth == 1

        events = g.undo()

        assert any(isinstance(e, StateReverted) for e in events)
        assert g.score == pre_score
        assert g.history.depth == 0

    def test_undo_restores_field(self):
        g = empty_game()
        g.new_game()
        row = PLAY_AREA_START + 2
        place(g, row, PLAY_AREA_END - 1, color=9)
        # Snapshot the pre-shot state.
        pre_innermost_color = g.field[row][LAUNCH_ZONE_DEPTH - 1].color_index

        g.shoot((row, PLAY_AREA_START - 1))
        g.undo()

        # Innermost ammo back to STAND with its original colour.
        assert g.field[row][LAUNCH_ZONE_DEPTH - 1].intention == CellIntention.STAND
        assert g.field[row][LAUNCH_ZONE_DEPTH - 1].color_index == pre_innermost_color


# --- game over ---------------------------------------------------------


class TestGameOver:
    def test_win_when_play_area_cleared(self):
        """An arbitrary shot that, after resolution, leaves the play area
        entirely void produces a GameOver(won=True) event."""
        g = Game(pick_color=lambda: 5, num_obstacles=0)
        g.new_game()
        # Manually clear the play area and set up a shot that leaves it empty.
        for r in range(PLAY_AREA_START, PLAY_AREA_END):
            for c in range(PLAY_AREA_START, PLAY_AREA_END):
                g.field[r][c] = Brick()
        # Put three same-colour bricks so the shot triggers a match and leaves
        # the play area empty afterwards.
        row = PLAY_AREA_START + 2
        place(g, row, PLAY_AREA_START + 1, color=5)
        place(g, row, PLAY_AREA_START + 2, color=5)

        events = g.shoot((row, PLAY_AREA_START - 1))

        go = [e for e in events if isinstance(e, GameOver)]
        assert go and go[0].won is True

    def test_no_game_over_when_shots_remain(self):
        g = empty_game()
        g.new_game()
        row = PLAY_AREA_START + 2
        place(g, row, PLAY_AREA_END - 1, color=9)

        events = g.shoot((row, PLAY_AREA_START - 1))

        assert not any(isinstance(e, GameOver) for e in events)


# --- event ordering ----------------------------------------------------


class TestEventOrdering:
    def test_brick_shot_precedes_moves_and_refills(self):
        g = empty_game()
        g.new_game()
        row = PLAY_AREA_START + 2
        place(g, row, PLAY_AREA_END - 1, color=9)

        events = g.shoot((row, PLAY_AREA_START - 1))

        shot_idx = next(i for i, e in enumerate(events) if isinstance(e, BrickShot))
        first_move_idx = next((i for i, e in enumerate(events) if isinstance(e, BrickMoved)), None)
        first_refill_idx = next((i for i, e in enumerate(events) if isinstance(e, LaunchZoneRefilled)), None)

        assert shot_idx == 0
        if first_move_idx is not None:
            assert first_move_idx > shot_idx
        if first_refill_idx is not None:
            assert first_refill_idx > shot_idx
