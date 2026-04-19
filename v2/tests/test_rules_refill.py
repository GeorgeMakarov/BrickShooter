"""Refill rule.

When a launcher queue has a VOID in it (ammo was fired, or a crosser shifted
one out), the remaining bricks shift inward and a fresh STAND brick appears
at the outermost cell. The rule emits:

- one BrickMoved event per brick that shifted inward;
- one LaunchZoneRefilled event per queue that got a new outermost brick.

Randomness is injected via a `pick_color` callable so tests stay deterministic.
"""

import itertools

from domain.brick import Brick, CellIntention
from domain.constants import FIELD_SIZE, LAUNCH_ZONE_DEPTH, PLAY_AREA_START, PLAY_AREA_END
from domain.events import BrickMoved, LaunchZoneRefilled
from domain.rules.refill import refill_launch_zones


def empty_field() -> list[list[Brick]]:
    return [[Brick() for _ in range(FIELD_SIZE)] for _ in range(FIELD_SIZE)]


def place(field, r: int, c: int, color: int = 0, intention: CellIntention = CellIntention.STAND) -> None:
    field[r][c] = Brick(intention=intention, color_index=color)


def fixed_color(n: int):
    """Returns a pick_color that always returns `n`."""
    return lambda: n


def sequential_colors(seq):
    """Returns a pick_color that yields the next value from `seq` on each call."""
    it = iter(seq)
    return lambda: next(it)


class TestNoVoids:
    def test_full_queues_produce_no_events(self):
        field = empty_field()
        row = PLAY_AREA_START + 1
        # Right launcher queue completely filled.
        for c in range(PLAY_AREA_END, FIELD_SIZE):
            place(field, row, c, color=1)

        events = refill_launch_zones(field, pick_color=fixed_color(9))

        # The row is one of 40 queues; the others are already empty/VOID, so
        # they'll also be refilled. The full queue specifically shouldn't change.
        changed_cells = {e.new_cell for e in events if isinstance(e, LaunchZoneRefilled)}
        assert (row, FIELD_SIZE - 1) not in changed_cells


class TestSingleQueueRefill:
    def test_void_in_innermost_slot_shifts_and_refills(self):
        field = empty_field()
        row = PLAY_AREA_START + 1
        # Right launcher queue: innermost VOID, then two bricks outward.
        place(field, row, PLAY_AREA_END + 1, color=5)
        place(field, row, PLAY_AREA_END + 2, color=6)
        # Empty the OTHER 39 queues aren't empty either — so the returned events
        # include refills everywhere. We filter by this row.

        events = refill_launch_zones(field, pick_color=fixed_color(7))

        row_events = _events_in_row(events, row)

        # One shift inward.
        moves = [e for e in row_events if isinstance(e, BrickMoved)]
        assert BrickMoved(from_cell=(row, PLAY_AREA_END + 1), to_cell=(row, PLAY_AREA_END)) in moves
        assert BrickMoved(from_cell=(row, PLAY_AREA_END + 2), to_cell=(row, PLAY_AREA_END + 1)) in moves

        # New brick at the outermost cell with the colour from pick_color.
        refills = [e for e in row_events if isinstance(e, LaunchZoneRefilled)]
        assert LaunchZoneRefilled(new_cell=(row, PLAY_AREA_END + 2), color_index=7) in refills

        # Field state: new brick is STAND with colour 7.
        outermost = field[row][PLAY_AREA_END + 2]
        assert outermost.intention == CellIntention.STAND
        assert outermost.color_index == 7

        # Shifted bricks retained their colours.
        assert field[row][PLAY_AREA_END].color_index == 5
        assert field[row][PLAY_AREA_END + 1].color_index == 6


class TestAllFourSides:
    """Every launcher side gets refilled in one pass."""

    def test_every_empty_side_produces_one_refill_per_cell(self):
        field = empty_field()
        # Field is entirely empty. All 40 queues will need refills.

        events = refill_launch_zones(field, pick_color=fixed_color(3))

        refills = [e for e in events if isinstance(e, LaunchZoneRefilled)]
        # Each of the 40 queues scans from innermost. The first VOID triggers
        # a shift + new outermost brick. Since the queue was entirely VOID,
        # the shift loop shifts VOIDs around and the outermost cell gets the
        # new brick. On the NEXT pass over the same queue (tests only call the
        # function once, so no re-scan) only that one refill fires per call.
        # Expect 40 queues * 1 refill per call = 40 events.
        assert len(refills) == 40


class TestDeterministicColour:
    def test_new_brick_colour_comes_from_pick_color(self):
        field = empty_field()
        row = PLAY_AREA_START + 1
        # Only the right launcher queue for `row` has a void; rest are already
        # filled to avoid those queues also consuming picks.
        _fill_all_queues_except(field, skip_row=row, skip_side="right")
        events = refill_launch_zones(field, pick_color=sequential_colors(itertools.count(1)))

        refills = [e for e in events if isinstance(e, LaunchZoneRefilled) and e.new_cell[0] == row]
        assert any(e.color_index == 1 for e in refills)


# --- helpers -------------------------------------------------------------

def _events_in_row(events, row):
    return [
        e for e in events
        if (isinstance(e, BrickMoved) and (e.from_cell[0] == row or e.to_cell[0] == row))
        or (isinstance(e, LaunchZoneRefilled) and e.new_cell[0] == row)
    ]


def _fill_all_queues_except(field, skip_row: int, skip_side: str) -> None:
    """Pre-populate every launcher queue to STAND so they need no refill, except
    the one specified so the test drives a single refill event."""
    # top + bottom for each play column
    for c in range(PLAY_AREA_START, PLAY_AREA_END):
        for r in range(LAUNCH_ZONE_DEPTH):            # top
            if not (skip_side == "top" and c == skip_row):
                place(field, r, c, color=0)
        for r in range(PLAY_AREA_END, FIELD_SIZE):     # bottom
            if not (skip_side == "bottom" and c == skip_row):
                place(field, r, c, color=0)
    # left + right for each play row
    for r in range(PLAY_AREA_START, PLAY_AREA_END):
        for c in range(LAUNCH_ZONE_DEPTH):            # left
            if not (skip_side == "left" and r == skip_row):
                place(field, r, c, color=0)
        for c in range(PLAY_AREA_END, FIELD_SIZE):     # right
            if not (skip_side == "right" and r == skip_row):
                place(field, r, c, color=0)
