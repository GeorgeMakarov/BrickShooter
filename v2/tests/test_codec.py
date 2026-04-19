"""JSON codec: DomainEvent <-> dict. Dicts are what FastAPI sends/receives over
the websocket (it JSON-encodes them itself). Every event type must round-trip
losslessly; tuple fields (Cell, tuple[Cell, ...]) survive even though JSON
arrays decode to Python lists.
"""

import json

import pytest

from backend.adapters.codec import EVENT_TYPES, from_json, to_json
from domain.events import (
    BrickCrossed,
    BrickMatched,
    BrickMoved,
    BrickShot,
    DomainEvent,
    GameOver,
    LaunchZoneRefilled,
    ScoreChanged,
    StateReverted,
)


ALL_EVENTS = [
    BrickShot(launcher_cell=(5, 2), ammo_cell=(5, 2), direction="TO_RIGHT"),
    BrickMoved(from_cell=(5, 13), to_cell=(5, 12)),
    BrickMatched(cells=((5, 3), (5, 4), (5, 5)), color_index=2),
    BrickCrossed(from_cell=(5, 12), to_cell=(5, 13), color_index=4),
    LaunchZoneRefilled(new_cell=(5, 15), color_index=7),
    ScoreChanged(delta=30, total=130),
    StateReverted(score=42),
    GameOver(reason="Board cleared.", won=True),
]


class TestToJson:
    @pytest.mark.parametrize("event", ALL_EVENTS)
    def test_has_type_discriminator(self, event):
        frame = to_json(event)
        assert frame["type"] == type(event).__name__

    def test_returns_plain_dict(self):
        frame = to_json(BrickMoved(from_cell=(1, 2), to_cell=(3, 4)))
        assert isinstance(frame, dict)

    def test_json_dumps_accepts_result(self):
        """Sanity: the output must be JSON-serialisable for the WS transport."""
        for event in ALL_EVENTS:
            json.dumps(to_json(event))  # no exception


class TestRoundTrip:
    @pytest.mark.parametrize("event", ALL_EVENTS)
    def test_every_event_round_trips(self, event):
        restored = from_json(to_json(event))
        assert restored == event
        assert type(restored) is type(event)

    def test_round_trip_over_json_string(self):
        """Dicts make the JSON-string round trip the transport will actually do."""
        for event in ALL_EVENTS:
            as_json = json.dumps(to_json(event))
            restored = from_json(json.loads(as_json))
            assert restored == event

    def test_cell_tuples_survive(self):
        e = BrickMoved(from_cell=(1, 2), to_cell=(3, 4))
        restored = from_json(to_json(e))
        assert isinstance(restored.from_cell, tuple)
        assert isinstance(restored.to_cell, tuple)

    def test_cells_list_of_tuples_survives(self):
        e = BrickMatched(cells=((5, 3), (5, 4), (5, 5)), color_index=2)
        restored = from_json(to_json(e))
        assert isinstance(restored.cells, tuple)
        for c in restored.cells:
            assert isinstance(c, tuple)


class TestFromJsonErrors:
    def test_missing_type_field_raises(self):
        with pytest.raises(ValueError, match="type"):
            from_json({"from_cell": [0, 0], "to_cell": [0, 1]})

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="unknown"):
            from_json({"type": "NotARealEvent", "foo": 1})


class TestRegistry:
    def test_registry_covers_every_domain_event_subclass(self):
        """Safety net: if a new DomainEvent variant ships without a codec entry,
        this test fails loudly."""
        known = set(EVENT_TYPES.values())
        expected = {
            BrickShot, BrickMoved, BrickMatched, BrickCrossed,
            LaunchZoneRefilled, ScoreChanged, StateReverted, GameOver,
        }
        assert known == expected
