"""End-to-end FastAPI app test.

Drives the /ws endpoint with Starlette's TestClient. Every connection starts
with a `session` frame carrying the sid, followed by a snapshot. Messages
after that drive the game through the WebInput router.
"""

from fastapi.testclient import TestClient

from backend.app import SESSIONS, app
from domain.constants import PLAY_AREA_START


def _expect_session_and_snapshot(ws):
    session = ws.receive_json()
    assert session["type"] == "session"
    assert isinstance(session["id"], str) and session["id"]
    snapshot = ws.receive_json()
    assert snapshot["type"] == "snapshot"
    return session["id"], snapshot


class TestInitialHandshake:
    def test_first_two_frames_are_session_then_snapshot(self):
        with TestClient(app).websocket_connect("/ws") as ws:
            _, snapshot = _expect_session_and_snapshot(ws)
            assert snapshot["score"] == 0
            assert "field" in snapshot


class TestSessionPersistence:
    def test_same_sid_reuses_game_across_reconnect(self):
        SESSIONS.clear()
        client = TestClient(app)

        # First connect — new session, new game.
        with client.websocket_connect("/ws") as ws:
            sid, _ = _expect_session_and_snapshot(ws)
            # Mutate server state so we can detect continuity on reconnect.
            SESSIONS[sid].game.score = 777

        # Reconnect with that sid — same Game should be returned, score preserved.
        with client.websocket_connect(f"/ws?sid={sid}") as ws:
            session = ws.receive_json()
            assert session["id"] == sid
            snapshot = ws.receive_json()
            assert snapshot["type"] == "snapshot"
            assert snapshot["score"] == 777

    def test_unknown_sid_creates_new_game(self):
        SESSIONS.clear()
        client = TestClient(app)

        with client.websocket_connect("/ws?sid=stale-or-server-restarted") as ws:
            session = ws.receive_json()
            assert session["id"] != "stale-or-server-restarted"
            snapshot = ws.receive_json()
            assert snapshot["score"] == 0


class TestSessionCap:
    def test_new_connection_refused_when_cap_reached(self):
        """Once MAX_SESSIONS is reached, new connections receive an error frame
        and get closed with code 1013 (try again later)."""
        from backend import app as app_module

        SESSIONS.clear()
        original_cap = app_module.MAX_SESSIONS
        app_module.MAX_SESSIONS = 1
        try:
            client = TestClient(app)
            with client.websocket_connect("/ws") as ws1:
                _expect_session_and_snapshot(ws1)
                # Second connection should be refused.
                import pytest as _pytest
                from starlette.websockets import WebSocketDisconnect as WSD
                with _pytest.raises(WSD):
                    with client.websocket_connect("/ws") as ws2:
                        frame = ws2.receive_json()
                        assert frame["type"] == "error"
                        # Server will close the socket; a subsequent receive raises.
                        ws2.receive_json()
        finally:
            app_module.MAX_SESSIONS = original_cap


class TestNewGameWithDifficulty:
    def test_new_game_with_difficulty_replaces_the_game(self):
        SESSIONS.clear()
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            sid, _ = _expect_session_and_snapshot(ws)
            SESSIONS[sid].game.score = 100  # prove the Game gets replaced
            ws.send_json({"type": "new_game", "difficulty": "easy"})
            snap = ws.receive_json()
            assert snap["type"] == "snapshot"
            assert snap["score"] == 0
            # num_colors of the new Game should be 5 (easy preset).
            assert SESSIONS[sid].game.num_colors == 5


class TestUndoOnFreshGame:
    def test_undo_without_history_is_silent(self):
        with TestClient(app).websocket_connect("/ws") as ws:
            _expect_session_and_snapshot(ws)
            ws.send_json({"type": "undo"})
            # No events from an empty history — follow up with new_game to
            # confirm the socket is still alive.
            ws.send_json({"type": "new_game"})
            frame = ws.receive_json()
            assert frame["type"] == "snapshot"


class TestNewGameResendsSnapshot:
    def test_new_game_sends_fresh_snapshot(self):
        with TestClient(app).websocket_connect("/ws") as ws:
            _expect_session_and_snapshot(ws)
            ws.send_json({"type": "new_game"})
            frame = ws.receive_json()
            assert frame["type"] == "snapshot"
            assert frame["score"] == 0


class TestShoot:
    def test_shoot_returns_deterministic_socket(self):
        with TestClient(app).websocket_connect("/ws") as ws:
            _expect_session_and_snapshot(ws)
            row = PLAY_AREA_START + 2
            ws.send_json({"type": "shoot", "cell": [row, PLAY_AREA_START - 1]})
            # Shot may or may not fire depending on random obstacle placement.
            # Follow up with new_game and drain until a fresh snapshot arrives
            # — proves the socket stayed alive through whatever came back.
            ws.send_json({"type": "new_game"})
            frame = ws.receive_json()
            while frame["type"] != "snapshot":
                frame = ws.receive_json()
            assert frame["type"] == "snapshot"


class TestMalformedMessage:
    def test_unknown_type_returns_error_frame(self):
        with TestClient(app).websocket_connect("/ws") as ws:
            _expect_session_and_snapshot(ws)
            ws.send_json({"type": "teleport"})
            frame = ws.receive_json()
            assert frame["type"] == "error"
