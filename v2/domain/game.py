"""Game facade.

Owns the field, score, level, and undo history. Implements GameInputPort.
Returns domain events from every use case; adapters push those events to
their presenter.

Session model:
  - new_game() starts at level 1, score 0.
  - Each level puts (level + 1) obstacles in the play area on setup.
  - Clearing the play area emits LevelCleared and auto-advances: level + 1,
    new obstacles, score preserved.
  - GameOver(won=False) fires only when no shot is possible on the current
    board — that's the real session end; the scoreboard records it then.

Resolution cycle (after a shot): repeatedly run
  movement step → crosser step → (if no moves:) match step → refill step
until a full round produces no changes. A ScoreChanged is emitted after every
match batch.
"""

import random
from typing import Callable, Optional

from domain.brick import Brick, CellIntention
from domain.constants import (
    FIELD_SIZE,
    LAUNCH_ZONE_DEPTH,
    PLAY_AREA_START,
    PLAY_AREA_END,
)
from domain.events import (
    DomainEvent,
    GameOver,
    LevelCleared,
    ScoreChanged,
)
from domain.history import HistoryStack
from domain.rules.crosser import handle_board_crossers
from domain.rules.matching import find_and_remove_groups
from domain.rules.movement import movement_resolution_step
from domain.rules.refill import refill_launch_zones
from domain.rules.shot import can_shoot, shoot


Field = list[list[Brick]]
Cell = tuple[int, int]
PickColor = Callable[[], int]


class Game:
    def __init__(
        self,
        num_colors: int = 7,
        pick_color: Optional[PickColor] = None,
        num_obstacles: Optional[int] = None,
        rng: Optional[random.Random] = None,
    ) -> None:
        """
        `num_obstacles`:
          - None  → defaults to `level + 1` (progressive difficulty)
          - int   → fixed override, useful for deterministic tests
        """
        self.num_colors = num_colors
        self._rng = rng or random.Random()
        self._pick_color: PickColor = pick_color or (lambda: self._rng.randint(0, num_colors - 1))
        self._num_obstacles_override = num_obstacles
        self.level: int = 1
        self.field: Field = _empty_field()
        self.score: int = 0
        self.history = HistoryStack()
        # Chain depth within the current resolution cycle — reset on every
        # successful shoot(). The first match batch scores ×1, the second ×2,
        # the third ×3, and so on; refill-induced chain reactions reward the
        # player proportionally.
        self._chain_depth: int = 0

    @property
    def num_obstacles(self) -> int:
        if self._num_obstacles_override is not None:
            return self._num_obstacles_override
        return self.level + 1

    # --- GameInputPort -------------------------------------------------

    def new_game(self) -> list[DomainEvent]:
        self.level = 1
        self.score = 0
        self.history.clear()
        self._setup_board()
        # Caller reads the field directly for the initial draw; events start
        # flowing on the first action.
        return []

    def abandon(self) -> list[DomainEvent]:
        # Player chose to end the session early (e.g. switching difficulty
        # mid-game). Emits GameOver(won=False) so presenters and scoreboard
        # see the same lifecycle event as a natural loss. State is not reset
        # here — the subsequent new_game() does that.
        return [GameOver(reason="Game abandoned.", won=False, level=self.level, score=self.score)]

    def shoot(self, cell: Cell) -> list[DomainEvent]:
        # Record pre-shot state; pop if the shot doesn't fire.
        self.history.save(self.field, self.score)
        shot_events = shoot(self.field, cell)
        if not shot_events:
            # discard the speculative save
            self.history.revert()
            return []

        # New shot = new chain. Reset the multiplier before running the cycle.
        self._chain_depth = 0
        events: list[DomainEvent] = list(shot_events)
        events.extend(self._resolve())
        events.extend(self._check_level_or_game_over())
        return events

    def undo(self) -> list[DomainEvent]:
        events, snap = self.history.revert()
        if snap is None:
            return []
        self.field = snap.field
        self.score = snap.score
        return events

    # --- resolution cycle ----------------------------------------------

    def _resolve(self) -> list[DomainEvent]:
        events: list[DomainEvent] = []
        while True:
            moved = self._drain_movement()
            events.extend(moved)

            matches, base_delta = find_and_remove_groups(self.field)
            if matches:
                events.extend(matches)
                # Apply the chain multiplier: first match batch ×1,
                # second ×2, third ×3, … The client's "Combo xN" popup
                # maps one-to-one to this multiplier.
                self._chain_depth += 1
                delta = base_delta * self._chain_depth
                self.score += delta
                events.append(ScoreChanged(delta=delta, total=self.score))
                continue  # matches may unblock more movement

            refills = refill_launch_zones(self.field, self._pick_color)
            if refills:
                events.extend(refills)
                continue

            if not moved:
                break  # fully stable
        return events

    def _drain_movement(self) -> list[DomainEvent]:
        """Run movement + crosser until neither produces any event."""
        events: list[DomainEvent] = []
        while True:
            moves = movement_resolution_step(self.field)
            crossed = handle_board_crossers(self.field)
            events.extend(moves)
            events.extend(crossed)
            if not moves and not crossed:
                return events

    # --- level / game over ---------------------------------------------

    def _check_level_or_game_over(self) -> list[DomainEvent]:
        if _is_play_area_empty(self.field):
            cleared = self.level
            self.level += 1
            self.history.clear()  # can't undo across a level transition
            self._setup_board()
            return [LevelCleared(level=cleared)]
        if not _any_shot_possible(self.field):
            return [GameOver(reason="No more moves.", won=False, level=self.level, score=self.score)]
        return []

    # --- setup ---------------------------------------------------------

    def _setup_board(self) -> None:
        """Populate launchers and sprinkle obstacles in the play area. Leaves
        level/score/history alone."""
        self.field = _empty_field()
        for r, c in _all_launcher_cells():
            self.field[r][c] = Brick(
                intention=CellIntention.STAND,
                color_index=self._pick_color(),
            )
        placed = 0
        target = self.num_obstacles
        while placed < target:
            r = self._rng.randint(PLAY_AREA_START, PLAY_AREA_END - 1)
            c = self._rng.randint(PLAY_AREA_START, PLAY_AREA_END - 1)
            if self.field[r][c].intention == CellIntention.VOID:
                self.field[r][c] = Brick(
                    intention=CellIntention.STAND,
                    color_index=self._pick_color(),
                )
                placed += 1


# --- helpers -----------------------------------------------------------


def _empty_field() -> Field:
    return [[Brick() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]


def _all_launcher_cells() -> list[Cell]:
    cells: list[Cell] = []
    for r in range(PLAY_AREA_START, PLAY_AREA_END):
        for c in range(LAUNCH_ZONE_DEPTH):
            cells.append((r, c))
        for c in range(PLAY_AREA_END, FIELD_SIZE):
            cells.append((r, c))
    for c in range(PLAY_AREA_START, PLAY_AREA_END):
        for r in range(LAUNCH_ZONE_DEPTH):
            cells.append((r, c))
        for r in range(PLAY_AREA_END, FIELD_SIZE):
            cells.append((r, c))
    return cells


def _is_play_area_empty(field: Field) -> bool:
    return all(
        field[r][c].intention == CellIntention.VOID
        for r in range(PLAY_AREA_START, PLAY_AREA_END)
        for c in range(PLAY_AREA_START, PLAY_AREA_END)
    )


def _any_shot_possible(field: Field) -> bool:
    for r in range(PLAY_AREA_START, PLAY_AREA_END):
        if can_shoot(field, (r, PLAY_AREA_START - 1)):
            return True
        if can_shoot(field, (r, PLAY_AREA_END)):
            return True
    for c in range(PLAY_AREA_START, PLAY_AREA_END):
        if can_shoot(field, (PLAY_AREA_START - 1, c)):
            return True
        if can_shoot(field, (PLAY_AREA_END, c)):
            return True
    return False
