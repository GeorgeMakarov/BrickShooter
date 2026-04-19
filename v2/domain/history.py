"""Undo history — a LIFO of field + score snapshots.

`save` deep-copies the field so subsequent mutations don't leak into stored
states. `revert` pops the top snapshot and returns both the snapshot itself
(so the caller can restore) and the corresponding StateReverted event.
"""

from copy import deepcopy
from dataclasses import dataclass
from typing import Optional

from domain.brick import Brick
from domain.events import DomainEvent, StateReverted


Field = list[list[Brick]]


@dataclass
class Snapshot:
    field: Field
    score: int


class HistoryStack:
    def __init__(self) -> None:
        self._stack: list[Snapshot] = []

    @property
    def depth(self) -> int:
        return len(self._stack)

    def save(self, field: Field, score: int) -> None:
        self._stack.append(Snapshot(field=deepcopy(field), score=score))

    def revert(self) -> tuple[list[DomainEvent], Optional[Snapshot]]:
        if not self._stack:
            return [], None
        snap = self._stack.pop()
        return [StateReverted(score=snap.score)], snap

    def clear(self) -> None:
        self._stack.clear()
