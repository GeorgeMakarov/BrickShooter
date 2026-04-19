"""Encode the full game state as a single JSON frame.

Sent on connect (so the client can render the initial board) and on any
resync point. Distinct `type: "snapshot"` discriminator so the frontend
can dispatch it separately from DomainEvents.
"""

from domain.brick import Brick
from domain.game import Game


def encode_snapshot(game: Game) -> dict:
    return {
        "type": "snapshot",
        "score": game.score,
        "level": game.level,
        "field": [[_encode_brick(b) for b in row] for row in game.field],
    }


def _encode_brick(brick: Brick) -> dict:
    return {
        "intention": brick.intention.name,
        "color_index": brick.color_index,
    }
