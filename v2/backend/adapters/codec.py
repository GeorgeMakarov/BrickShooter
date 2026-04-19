"""JSON codec for DomainEvents.

`to_json` converts an event into a plain `dict` suitable for JSON encoding.
`from_json` reconstructs an event from a decoded JSON dict. A `type`
discriminator field (matching the class name) is added on encode and used on
decode.

Tuple fields (`Cell = tuple[int, int]` and `cells: tuple[Cell, ...]`) are
restored from their JSON-array forms since `json.loads` returns lists.
"""

import dataclasses
from typing import Any, Callable

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


EVENT_TYPES: dict[str, type[DomainEvent]] = {
    cls.__name__: cls
    for cls in (
        BrickShot,
        BrickMoved,
        BrickMatched,
        BrickCrossed,
        LaunchZoneRefilled,
        ScoreChanged,
        StateReverted,
        GameOver,
    )
}


# Field-name -> restorer. Any event field that should come back as a tuple
# (Python dataclasses accept either, but __eq__ cares) is listed here.
_FIELD_RESTORERS: dict[str, Callable[[Any], Any]] = {
    "launcher_cell": tuple,
    "ammo_cell": tuple,
    "from_cell": tuple,
    "to_cell": tuple,
    "new_cell": tuple,
    "cells": lambda v: tuple(tuple(c) for c in v),
}


def to_json(event: DomainEvent) -> dict:
    """Encode `event` as a JSON-serialisable dict with a `type` discriminator."""
    payload = dataclasses.asdict(event)
    payload["type"] = type(event).__name__
    return payload


def from_json(frame: dict) -> DomainEvent:
    """Decode a previously-encoded dict back into the concrete event."""
    type_name = frame.get("type")
    if type_name is None:
        raise ValueError("JSON frame missing 'type' field")
    cls = EVENT_TYPES.get(type_name)
    if cls is None:
        raise ValueError(f"unknown event type: {type_name}")

    kwargs = {}
    for field in dataclasses.fields(cls):
        if field.name not in frame:
            continue
        value = frame[field.name]
        restorer = _FIELD_RESTORERS.get(field.name)
        kwargs[field.name] = restorer(value) if restorer else value

    return cls(**kwargs)
