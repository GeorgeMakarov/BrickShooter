"""WebPresenter buffers domain events as JSON frames for later flushing over a
websocket. The game loop calls on_event synchronously; the async WS handler
drains the buffer after each input-port call and sends the frames in order.
"""

from backend.adapters.web_presenter import WebPresenter
from domain.events import BrickMoved, ScoreChanged
from domain.ports import GamePresenterPort


def test_implements_game_presenter_port():
    assert isinstance(WebPresenter(), GamePresenterPort)


class TestBuffering:
    def test_on_event_appends_encoded_frame(self):
        p = WebPresenter()
        p.on_event(BrickMoved(from_cell=(0, 0), to_cell=(0, 1)))

        frames = p.drain()
        assert len(frames) == 1
        assert frames[0]["type"] == "BrickMoved"
        assert frames[0]["to_cell"] == [0, 1]

    def test_multiple_events_accumulate_in_order(self):
        p = WebPresenter()
        p.on_event(BrickMoved(from_cell=(0, 0), to_cell=(0, 1)))
        p.on_event(ScoreChanged(delta=10, total=10))

        frames = p.drain()
        assert [f["type"] for f in frames] == ["BrickMoved", "ScoreChanged"]

    def test_drain_empties_buffer(self):
        p = WebPresenter()
        p.on_event(ScoreChanged(delta=5, total=5))
        p.drain()
        assert p.drain() == []

    def test_drain_on_empty_buffer_returns_empty_list(self):
        assert WebPresenter().drain() == []
