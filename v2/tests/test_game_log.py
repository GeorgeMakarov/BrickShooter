"""Smoke tests for the gameplay logger.

Verifies every helper emits a well-shaped log line tagged with the session id,
so `grep sid=XYZ server.log` extracts a full user session for investigation.
"""

import logging

import pytest

from backend.game_log import (
    log_evict,
    log_in,
    log_join,
    log_leave,
    log_out,
    log_snapshot,
)
from domain.events import BrickMoved
from domain.game import Game


@pytest.fixture
def caplog_game(caplog):
    caplog.set_level(logging.DEBUG, logger="brickshooter.game")
    return caplog


def test_join_log_carries_sid_and_client(caplog_game):
    log_join("abc123", "127.0.0.1:5555")
    text = caplog_game.text
    assert "JOIN" in text
    assert "sid=abc123" in text
    assert "client=127.0.0.1:5555" in text


def test_leave_and_evict_are_tagged(caplog_game):
    log_leave("abc123")
    log_evict("xyz789")
    assert "LEAVE sid=abc123" in caplog_game.text
    assert "EVICT sid=xyz789" in caplog_game.text


def test_in_logs_the_message(caplog_game):
    log_in("abc123", {"type": "shoot", "cell": [5, 2]})
    assert "IN sid=abc123" in caplog_game.text
    assert '"shoot"' in caplog_game.text
    assert "[5,2]" in caplog_game.text  # compact JSON, no spaces


def test_out_logs_event_type_and_payload(caplog_game):
    log_out("abc123", BrickMoved(from_cell=(5, 13), to_cell=(5, 12)))
    assert "OUT sid=abc123" in caplog_game.text
    assert "ev=BrickMoved" in caplog_game.text
    # from_cell/to_cell become [5, 13] style in the JSON.
    assert "from_cell" in caplog_game.text


def test_snapshot_logs_score_and_hash(caplog_game):
    g = Game(pick_color=lambda: 0, num_obstacles=0)
    g.new_game()
    log_snapshot("abc123", g)
    assert "SNAPSHOT sid=abc123" in caplog_game.text
    assert "score=0" in caplog_game.text
    assert "hash=" in caplog_game.text


def test_snapshot_includes_field_at_debug_level(caplog_game):
    g = Game(pick_color=lambda: 0, num_obstacles=0)
    g.new_game()
    log_snapshot("abc123", g)
    # DEBUG level was set in the fixture; full field should be present.
    assert "field=" in caplog_game.text
