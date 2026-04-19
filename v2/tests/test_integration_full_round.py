"""End-to-end domain integration test.

Drives a `Game` through a full round — new_game, a shot that triggers a match,
refill, then undo — via the input port, piping every domain event into a fake
`GamePresenterPort`. Proves the event stream the adapters will consume is
coherent, ordered, and round-trips through history correctly.

No v1 code is touched: v1 stays frozen at `v1-final` as the visual reference.
"""

from domain.brick import Brick, CellIntention
from domain.constants import LAUNCH_ZONE_DEPTH, PLAY_AREA_START, PLAY_AREA_END
from domain.events import (
    BrickMatched,
    BrickMoved,
    BrickShot,
    DomainEvent,
    LaunchZoneRefilled,
    ScoreChanged,
    StateReverted,
)
from domain.game import Game
from domain.ports import GameInputPort, GamePresenterPort


class RecordingPresenter:
    """Fake presenter — records every event in order."""

    def __init__(self) -> None:
        self.received: list[DomainEvent] = []

    def on_event(self, event: DomainEvent) -> None:
        self.received.append(event)

    def by_type(self, t):
        return [e for e in self.received if isinstance(e, t)]


def drive(input_port: GameInputPort, presenter: GamePresenterPort, fn, *args):
    """Call an input-port method and fan the returned events to the presenter."""
    for e in fn(*args):
        presenter.on_event(e)


def test_full_round_shot_match_refill_undo():
    # Deterministic colour stream. First call returns 7 (used for match),
    # subsequent calls return 3 (so refills don't accidentally form new matches).
    colours = iter([7] * 60 + [3] * 1000)
    game = Game(pick_color=lambda: next(colours), num_obstacles=0)
    presenter = RecordingPresenter()

    # Contract sanity.
    assert isinstance(game, GameInputPort)
    assert isinstance(presenter, GamePresenterPort)

    # --- setup ---------------------------------------------------------
    drive(game, presenter, game.new_game)
    # After new_game every launcher cell is STAND with colour 7 (from the
    # deterministic stream). Place a colour-7 pair in the play area so the
    # shot completes a triplet, plus one obstacle so the shot fires.
    row = PLAY_AREA_START + 2
    game.field[row][PLAY_AREA_START + 1] = Brick(CellIntention.STAND, color_index=7)
    game.field[row][PLAY_AREA_START + 2] = Brick(CellIntention.STAND, color_index=7)
    # Obstacle in the same row so the shot has a target to hit.
    game.field[row][PLAY_AREA_END - 1] = Brick(CellIntention.STAND, color_index=9)

    # --- fire the shot -------------------------------------------------
    pre_score = game.score
    pre_history_depth = game.history.depth
    drive(game, presenter, game.shoot, (row, PLAY_AREA_START - 1))

    # First event is the BrickShot; history grew by one snapshot.
    assert isinstance(presenter.received[0], BrickShot)
    assert game.history.depth == pre_history_depth + 1

    # Ammo brick traversed multiple cells → at least one BrickMoved.
    moves = presenter.by_type(BrickMoved)
    assert moves, "ammo should have moved at least once"

    # Match happened and the score reflects it.
    matches = presenter.by_type(BrickMatched)
    assert matches, "a colour-7 triplet should have matched"
    score_changes = presenter.by_type(ScoreChanged)
    assert score_changes, "matching emits ScoreChanged"
    assert game.score > pre_score
    assert score_changes[-1].total == game.score

    # Launcher refilled to replace the used ammo.
    assert presenter.by_type(LaunchZoneRefilled)

    # --- undo ----------------------------------------------------------
    mid_round_score = game.score
    drive(game, presenter, game.undo)

    reverts = presenter.by_type(StateReverted)
    assert len(reverts) == 1
    assert reverts[0].score == pre_score
    assert game.score == pre_score
    assert game.history.depth == 0

    # --- ordering sanity ----------------------------------------------
    # BrickShot strictly precedes the first BrickMoved.
    shot_idx = next(i for i, e in enumerate(presenter.received) if isinstance(e, BrickShot))
    first_move_idx = next(i for i, e in enumerate(presenter.received) if isinstance(e, BrickMoved))
    assert shot_idx < first_move_idx

    # BrickMatched precedes its ScoreChanged.
    match_idx = next(i for i, e in enumerate(presenter.received) if isinstance(e, BrickMatched))
    score_idx = next(i for i, e in enumerate(presenter.received) if isinstance(e, ScoreChanged))
    assert match_idx < score_idx

    # StateReverted came last (after the whole resolution cycle finished).
    revert_idx = next(i for i, e in enumerate(presenter.received) if isinstance(e, StateReverted))
    assert revert_idx == len(presenter.received) - 1
