"""Per-session gameplay-log helpers.

Each log line starts with a `sid=XYZ` tag so a full session can be extracted
with a single grep. Line shapes:

  JOIN sid=XYZ client=IP:PORT
  LEAVE sid=XYZ
  EVICT sid=XYZ
  IN  sid=XYZ msg=<json>
  OUT sid=XYZ ev=<EventName> payload=<json>
  SNAPSHOT sid=XYZ score=N hash=H [field=...]   (field only at DEBUG level)
"""

import dataclasses
import hashlib
import json
import logging
from typing import TYPE_CHECKING

from domain.brick import CellIntention
from domain.events import DomainEvent

if TYPE_CHECKING:
    from domain.game import Game


log = logging.getLogger("brickshooter.game")

# Single char per CellIntention, for the compact field blob.
_INTENTION_CHAR = {
    CellIntention.VOID: "V",
    CellIntention.STAND: "S",
    CellIntention.TO_LEFT: "L",
    CellIntention.TO_RIGHT: "R",
    CellIntention.TO_UP: "U",
    CellIntention.TO_DOWN: "D",
}


def log_join(sid: str, client: str) -> None:
    log.info("JOIN sid=%s client=%s", sid, client)


def log_leave(sid: str) -> None:
    log.info("LEAVE sid=%s", sid)


def log_evict(sid: str) -> None:
    log.info("EVICT sid=%s", sid)


def log_in(sid: str, message: object) -> None:
    log.info("IN sid=%s msg=%s", sid, _compact_json(message))


def log_out(sid: str, event: DomainEvent) -> None:
    payload = {k: v for k, v in dataclasses.asdict(event).items()}
    log.info("OUT sid=%s ev=%s payload=%s", sid, type(event).__name__, _compact_json(payload))


def log_snapshot(sid: str, game: "Game") -> None:
    blob = _encode_field(game)
    digest = hashlib.sha1(blob.encode()).hexdigest()[:10]
    # Full field only at DEBUG level — at INFO keep lines short.
    if log.isEnabledFor(logging.DEBUG):
        log.info("SNAPSHOT sid=%s score=%d hash=%s field=%s", sid, game.score, digest, blob)
    else:
        log.info("SNAPSHOT sid=%s score=%d hash=%s", sid, game.score, digest)


def _compact_json(obj: object) -> str:
    return json.dumps(obj, separators=(",", ":"), default=str)


def _encode_field(game: "Game") -> str:
    """256-char blob, two chars per cell: intention letter + color digit (or _).

    Row separator `/` for readability. Reconstructible back to the full field
    without ambiguity.
    """
    rows: list[str] = []
    for row in game.field:
        parts: list[str] = []
        for brick in row:
            ch = _INTENTION_CHAR.get(brick.intention, "?")
            c = str(brick.color_index) if brick.color_index is not None else "_"
            parts.append(f"{ch}{c}")
        rows.append("".join(parts))
    return "/".join(rows)
