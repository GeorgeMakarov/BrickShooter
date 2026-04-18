"""Behavioural spec for the v1 game model.

These tests capture the rules the Godot port must match. Each test sets up an
explicit board state, runs one model operation, and asserts the outcome.
"""

import random

import pytest

from model import (
    FIELD_SIZE,
    LAUNCH_ZONE_DEPTH,
    PLAY_AREA_START,
    PLAY_AREA_END,
    Brick,
    CellIntention,
    GameModel,
)


def empty_model(num_colors: int = 7) -> GameModel:
    """GameModel with a fully-VOID 16x16 field. Bypasses new_game() randomness."""
    m = GameModel(num_colors=num_colors)
    m.field = [[Brick() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]
    m.score = 0
    m.history.clear()
    return m


def place(m: GameModel, r: int, c: int, color: int, intention: CellIntention = CellIntention.STAND) -> None:
    m.field[r][c] = Brick(intention=intention, color_index=color)


# --- shot rules ----------------------------------------------------------

class TestShootBrick:
    def test_valid_left_launcher_shot_sets_direction(self):
        m = empty_model()
        row = PLAY_AREA_START + 2
        # Fill left launcher row with ammo; leave play-area cells empty except a target obstacle.
        for c in range(LAUNCH_ZONE_DEPTH):
            place(m, row, c, color=0)
        # Obstacle in the path so shot is non-trivial.
        place(m, row, PLAY_AREA_END - 1, color=1)

        assert m.shoot_brick(row, PLAY_AREA_START - 1) is True
        # Innermost ammo brick is the one that gets the directional intention.
        innermost = m.field[row][LAUNCH_ZONE_DEPTH - 1]
        assert innermost.intention == CellIntention.TO_RIGHT

    def test_shot_fails_when_target_edge_occupied(self):
        m = empty_model()
        row = PLAY_AREA_START + 2
        for c in range(LAUNCH_ZONE_DEPTH):
            place(m, row, c, color=0)
        place(m, row, PLAY_AREA_START, color=1)  # target edge occupied

        assert m.shoot_brick(row, PLAY_AREA_START - 1) is False

    def test_shot_fails_when_no_obstacle_in_path(self):
        m = empty_model()
        row = PLAY_AREA_START + 2
        for c in range(LAUNCH_ZONE_DEPTH):
            place(m, row, c, color=0)
        # No obstacle anywhere in play area along the row.

        assert m.shoot_brick(row, PLAY_AREA_START - 1) is False

    def test_tap_outside_launcher_row_ignored(self):
        m = empty_model()
        # Tap in the middle of the play area — not a launcher cell.
        assert m.shoot_brick(PLAY_AREA_START + 2, PLAY_AREA_START + 2) is False


# --- movement resolution ------------------------------------------------

class TestMovementResolution:
    def test_brick_with_directional_intent_moves_one_cell(self):
        m = empty_model()
        row = PLAY_AREA_START + 1
        place(m, row, PLAY_AREA_START + 5, color=0, intention=CellIntention.TO_LEFT)

        moves = m.movement_resolution_step()

        assert moves == [((row, PLAY_AREA_START + 5), (row, PLAY_AREA_START + 4))]
        assert m.field[row][PLAY_AREA_START + 4].intention == CellIntention.TO_LEFT
        assert m.field[row][PLAY_AREA_START + 5].intention == CellIntention.VOID

    def test_brick_blocked_by_non_void_neighbour_does_not_move(self):
        m = empty_model()
        row = PLAY_AREA_START + 1
        place(m, row, PLAY_AREA_START + 5, color=0, intention=CellIntention.TO_LEFT)
        place(m, row, PLAY_AREA_START + 4, color=1)  # blocker

        moves = m.movement_resolution_step()

        assert moves == []
        assert m.field[row][PLAY_AREA_START + 5].intention == CellIntention.TO_LEFT

    def test_brick_in_play_area_does_not_exit_via_move(self):
        """A brick at the inside edge of the play area with outward intention
        must stay put; crossing is handled separately by handle_board_crossers."""
        m = empty_model()
        row = PLAY_AREA_START + 1
        place(m, row, PLAY_AREA_START, color=0, intention=CellIntention.TO_LEFT)

        moves = m.movement_resolution_step()

        assert moves == []
        assert m.field[row][PLAY_AREA_START].intention == CellIntention.TO_LEFT


# --- match removal + scoring -------------------------------------------

class TestFindAndRemoveGroups:
    def test_horizontal_triplet_removed_and_scored(self):
        m = empty_model()
        row = PLAY_AREA_START + 2
        for dc in range(3):
            place(m, row, PLAY_AREA_START + dc, color=4)

        removed, score = m.find_and_remove_groups()

        assert len(removed) == 3
        assert all(m.field[r][c].intention == CellIntention.VOID for r, c in removed)
        assert score > 0
        assert m.score == score

    def test_vertical_triplet_removed(self):
        m = empty_model()
        col = PLAY_AREA_START + 2
        for dr in range(3):
            place(m, PLAY_AREA_START + dr, col, color=2)

        removed, _ = m.find_and_remove_groups()

        assert len(removed) == 3

    def test_pair_not_removed(self):
        m = empty_model()
        row = PLAY_AREA_START + 2
        for dc in range(2):
            place(m, row, PLAY_AREA_START + dc, color=4)

        removed, score = m.find_and_remove_groups()

        assert removed == []
        assert score == 0

    def test_larger_group_scores_more_than_minimum(self):
        m_small = empty_model()
        m_big = empty_model()
        row = PLAY_AREA_START + 2
        for dc in range(3):
            place(m_small, row, PLAY_AREA_START + dc, color=4)
        for dc in range(5):
            place(m_big, row, PLAY_AREA_START + dc, color=4)

        _, score_small = m_small.find_and_remove_groups()
        _, score_big = m_big.find_and_remove_groups()

        assert score_big > score_small

    def test_matches_only_consider_play_area(self):
        """Bricks inside a launcher zone should not be part of match groups."""
        m = empty_model()
        row = PLAY_AREA_START + 2
        # Place three same-colour bricks straddling the launcher / play boundary.
        place(m, row, PLAY_AREA_START - 2, color=4)  # launcher
        place(m, row, PLAY_AREA_START - 1, color=4)  # launcher
        place(m, row, PLAY_AREA_START, color=4)      # play area edge

        removed, _ = m.find_and_remove_groups()

        assert removed == []


# --- crossers and refill ------------------------------------------------

class TestBoardCrossers:
    def test_brick_at_right_edge_with_to_right_crosses_into_launcher(self):
        m = empty_model()
        row = PLAY_AREA_START + 1
        place(m, row, PLAY_AREA_END - 1, color=3, intention=CellIntention.TO_RIGHT)

        changed = m.handle_board_crossers()

        assert changed is True
        # Crosser lands in the innermost right-launcher cell and becomes STAND.
        landed = m.field[row][PLAY_AREA_END]
        assert landed.intention == CellIntention.STAND
        assert landed.color_index == 3
        # Source cell is cleared.
        assert m.field[row][PLAY_AREA_END - 1].intention == CellIntention.VOID

    def test_non_crossing_brick_left_alone(self):
        m = empty_model()
        place(m, PLAY_AREA_START + 1, PLAY_AREA_START + 5, color=3, intention=CellIntention.TO_RIGHT)
        assert m.handle_board_crossers() is False


class TestRefillLaunchZones:
    def test_void_in_launcher_queue_shifts_and_adds_new(self):
        random.seed(42)  # deterministic colour for the refilled outermost cell
        m = empty_model()
        row = PLAY_AREA_START + 1
        # Right launcher queue: innermost VOID, middle and outer filled.
        place(m, row, PLAY_AREA_END + 1, color=5)
        place(m, row, PLAY_AREA_END + 2, color=6)
        # PLAY_AREA_END is VOID by default.

        changed = m.refill_launch_zones()

        assert changed is True
        # Shift pulled inward; outermost gets new STAND brick.
        assert m.field[row][PLAY_AREA_END].intention == CellIntention.STAND
        assert m.field[row][PLAY_AREA_END + 2].intention == CellIntention.STAND


# --- history / undo -----------------------------------------------------

class TestHistory:
    def test_save_and_revert_restores_field_and_score(self):
        m = empty_model()
        place(m, PLAY_AREA_START, PLAY_AREA_START, color=7)
        m.score = 100

        m.save_state()
        # Mutate state after snapshot.
        m.field[PLAY_AREA_START][PLAY_AREA_START] = Brick()
        m.score = 999

        assert m.revert_to_previous_state() is True
        assert m.field[PLAY_AREA_START][PLAY_AREA_START].color_index == 7
        assert m.score == 100

    def test_revert_with_empty_history_returns_false(self):
        m = empty_model()
        assert m.revert_to_previous_state() is False

    def test_save_deep_copies_field(self):
        """Mutating the live field after save_state must not affect the snapshot."""
        m = empty_model()
        place(m, PLAY_AREA_START, PLAY_AREA_START, color=7)
        m.save_state()
        m.field[PLAY_AREA_START][PLAY_AREA_START].color_index = 99
        m.revert_to_previous_state()
        assert m.field[PLAY_AREA_START][PLAY_AREA_START].color_index == 7


# --- game-over conditions ----------------------------------------------

class TestGameOver:
    def test_empty_play_area_is_a_win(self):
        m = empty_model()
        # Play area is all VOID; launchers empty too.
        is_over, reason = m.is_game_over()
        assert is_over is True
        assert "win" in reason.lower() or "clear" in reason.lower()

    def test_active_game_with_possible_shot_is_not_over(self):
        m = empty_model()
        row = PLAY_AREA_START + 2
        # Ammo in left launcher, obstacle in play area → shot possible.
        for c in range(LAUNCH_ZONE_DEPTH):
            place(m, row, c, color=0)
        place(m, row, PLAY_AREA_END - 1, color=1)

        is_over, _ = m.is_game_over()
        assert is_over is False
