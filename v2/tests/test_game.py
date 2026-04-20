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
    LevelCleared,
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


class TestChainBonus:
    def _seed_triplet(self, g: Game, row_offset: int = 2) -> None:
        row = PLAY_AREA_START + row_offset
        for dc in range(3):
            place(g, row, PLAY_AREA_START + dc, color=5)

    def test_first_match_in_cycle_scores_x1(self):
        g = Game(pick_color=lambda: 5, num_obstacles=0)
        g.new_game()
        self._seed_triplet(g)

        events = g._resolve()  # type: ignore[attr-defined]
        score_events = [e for e in events if isinstance(e, ScoreChanged)]

        assert len(score_events) == 1
        assert score_events[0].delta == 30  # group of 3 at multiplier x1

    def test_second_match_scores_x2(self):
        """Drive two resolution passes without an intervening shot() call —
        the second pass inherits the chain depth, so its delta doubles."""
        g = Game(pick_color=lambda: 5, num_obstacles=0)
        g.new_game()
        # First match: advance chain_depth to 1.
        self._seed_triplet(g, row_offset=2)
        first = g._resolve()  # type: ignore[attr-defined]
        first_score = next(e for e in first if isinstance(e, ScoreChanged))
        assert first_score.delta == 30

        # Second match: chain_depth goes 1 -> 2, delta doubles.
        self._seed_triplet(g, row_offset=4)
        second = g._resolve()  # type: ignore[attr-defined]
        second_score = next(e for e in second if isinstance(e, ScoreChanged))
        assert second_score.delta == 60  # 30 * 2

    def test_shoot_resets_chain_depth(self):
        g = Game(pick_color=lambda: 5, num_obstacles=0)
        g.new_game()
        # Pretend a previous cycle left a stale chain counter.
        g._chain_depth = 99
        row = PLAY_AREA_START + 2
        place(g, row, PLAY_AREA_END - 1, color=9)  # obstacle so shot fires

        g.shoot((row, PLAY_AREA_START - 1))

        # Chain depth reflects match batches produced this shot only —
        # 0 (no match) or 1 (one batch). Certainly not 100+.
        assert g._chain_depth <= 1


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


class TestLevelProgression:
    def test_clearing_play_area_emits_level_cleared_not_game_over(self):
        """Sessions continue across a cleared level: emit LevelCleared,
        advance the level, rebuild the board, keep the score."""
        g = Game(pick_color=lambda: 5, num_obstacles=0)
        g.new_game()
        pre_level = g.level
        # Manually clear the play area, place a colour-5 pair so the shot
        # completes a triplet and leaves the play area empty.
        for r in range(PLAY_AREA_START, PLAY_AREA_END):
            for c in range(PLAY_AREA_START, PLAY_AREA_END):
                g.field[r][c] = Brick()
        row = PLAY_AREA_START + 2
        place(g, row, PLAY_AREA_START + 1, color=5)
        place(g, row, PLAY_AREA_START + 2, color=5)

        events = g.shoot((row, PLAY_AREA_START - 1))

        cleared = [e for e in events if isinstance(e, LevelCleared)]
        assert cleared, "expected LevelCleared"
        assert cleared[0].level == pre_level
        # GameOver should NOT fire on a clear.
        assert not any(isinstance(e, GameOver) for e in events)
        # Level bumped.
        assert g.level == pre_level + 1

    def test_score_persists_across_level_advance(self):
        g = Game(pick_color=lambda: 5, num_obstacles=0)
        g.new_game()
        g.score = 150  # pretend we scored earlier
        for r in range(PLAY_AREA_START, PLAY_AREA_END):
            for c in range(PLAY_AREA_START, PLAY_AREA_END):
                g.field[r][c] = Brick()
        row = PLAY_AREA_START + 2
        place(g, row, PLAY_AREA_START + 1, color=5)
        place(g, row, PLAY_AREA_START + 2, color=5)

        g.shoot((row, PLAY_AREA_START - 1))

        # Match added points; bump is the base 30 (3 * 10 * 1) plus whatever.
        # The important invariant: score didn't reset.
        assert g.score >= 150

    def test_next_level_has_more_obstacles(self):
        """level 1 → 2 obstacles; after clearing, level 2 → 3 obstacles."""
        g = Game(pick_color=lambda: 5)  # no override — level-based obstacles
        g.new_game()
        assert g.num_obstacles == 2

        # Short-cut: clear the play area and poke _check_level_or_game_over
        # directly; the integration test above exercises the full flow.
        for r in range(PLAY_AREA_START, PLAY_AREA_END):
            for c in range(PLAY_AREA_START, PLAY_AREA_END):
                g.field[r][c] = Brick()
        events = g._check_level_or_game_over()  # type: ignore[attr-defined]
        assert any(isinstance(e, LevelCleared) for e in events)
        assert g.level == 2
        assert g.num_obstacles == 3
        # Play area now has exactly 3 STAND bricks (the new level's obstacles).
        obstacles = [
            (r, c)
            for r in range(PLAY_AREA_START, PLAY_AREA_END)
            for c in range(PLAY_AREA_START, PLAY_AREA_END)
            if g.field[r][c].intention == CellIntention.STAND
        ]
        assert len(obstacles) == 3

    def test_history_cleared_across_level_transition(self):
        """Undo must not cross level boundaries — the pre-clear field no
        longer exists once the new level sets up."""
        g = Game(pick_color=lambda: 5, num_obstacles=0)
        g.new_game()
        # Seed one saved snapshot so history isn't already empty.
        g.history.save(g.field, 0)
        assert g.history.depth == 1
        for r in range(PLAY_AREA_START, PLAY_AREA_END):
            for c in range(PLAY_AREA_START, PLAY_AREA_END):
                g.field[r][c] = Brick()

        g._check_level_or_game_over()  # type: ignore[attr-defined]

        assert g.history.depth == 0


class TestGameOver:
    def test_no_game_over_when_shots_remain(self):
        g = empty_game()
        g.new_game()
        row = PLAY_AREA_START + 2
        place(g, row, PLAY_AREA_END - 1, color=9)

        events = g.shoot((row, PLAY_AREA_START - 1))

        assert not any(isinstance(e, GameOver) for e in events)

    def test_game_over_carries_level_and_score(self):
        g = Game(pick_color=lambda: 5, num_obstacles=0)
        g.new_game()
        g.level = 3
        g.score = 240
        # Empty the entire board (play + launchers) so no shot is possible.
        for r in range(FIELD_SIZE):
            for c in range(FIELD_SIZE):
                g.field[r][c] = Brick()
        # Add a single lone brick in the play area so it isn't treated as an
        # empty-area win.
        place(g, PLAY_AREA_START + 2, PLAY_AREA_START + 2, color=1)

        events = g._check_level_or_game_over()  # type: ignore[attr-defined]

        go = [e for e in events if isinstance(e, GameOver)]
        assert go and go[0].won is False
        assert go[0].level == 3
        assert go[0].score == 240


# --- abandon -----------------------------------------------------------


class TestAbandon:
    def test_abandon_emits_game_over_lost(self):
        g = empty_game()
        g.new_game()
        g.level = 4
        g.score = 987

        events = g.abandon()

        go = [e for e in events if isinstance(e, GameOver)]
        assert go and go[0].won is False
        assert go[0].level == 4
        assert go[0].score == 987

    def test_abandon_does_not_mutate_state(self):
        g = empty_game()
        g.new_game()
        g.level = 2
        g.score = 40
        field_snapshot = [row[:] for row in g.field]

        g.abandon()

        assert g.level == 2
        assert g.score == 40
        assert g.field == field_snapshot


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
