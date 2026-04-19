"""Snapshot encoder.

Serialises the whole field + score as a single JSON frame with a distinct
`type: "snapshot"` discriminator (separate from DomainEvents). Clients use it
to render the initial state on connect, and on explicit resync requests.
"""

from backend.adapters.snapshot import encode_snapshot
from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, PLAY_AREA_START
from domain.game import Game


def test_snapshot_has_type_discriminator():
    g = Game(pick_color=lambda: 3)
    g.new_game()
    frame = encode_snapshot(g)
    assert frame["type"] == "snapshot"


def test_snapshot_includes_score():
    g = Game(pick_color=lambda: 3)
    g.new_game()
    g.score = 42
    frame = encode_snapshot(g)
    assert frame["score"] == 42


def test_snapshot_field_matches_dimensions():
    g = Game(pick_color=lambda: 3)
    g.new_game()
    frame = encode_snapshot(g)
    assert len(frame["field"]) == FIELD_SIZE
    assert all(len(row) == FIELD_SIZE for row in frame["field"])


def test_brick_serialised_as_intention_name_and_colour():
    g = Game(pick_color=lambda: 0)
    g.new_game()
    r, c = PLAY_AREA_START + 2, PLAY_AREA_START + 2
    g.field[r][c] = Brick(intention=CellIntention.STAND, color_index=5)

    frame = encode_snapshot(g)

    cell = frame["field"][r][c]
    assert cell["intention"] == "STAND"
    assert cell["color_index"] == 5


def test_void_cell_is_serialised_with_null_color():
    g = Game(pick_color=lambda: 0)
    g.new_game()
    # Pick a cell that's guaranteed VOID: centre of the play area.
    r, c = PLAY_AREA_START + 4, PLAY_AREA_START + 4
    g.field[r][c] = Brick()

    frame = encode_snapshot(g)

    cell = frame["field"][r][c]
    assert cell["intention"] == "VOID"
    assert cell["color_index"] is None
