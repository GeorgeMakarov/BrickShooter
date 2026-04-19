"""Server-side high-score table.

Stores a JSON array under `BRICKSHOOTER_SCORES_FILE` (default
`/var/lib/brickshooter/scores.json`). Writes are atomic (tmp file + rename),
so concurrent GameOver records never corrupt the file.

Per-difficulty top-N (default 50) is kept. Queries filter by difficulty and
return the top `limit` entries.

On a corrupt file (manual edit gone wrong, half-written from an OS crash),
the file is renamed aside to `.corrupt` and the scoreboard resumes empty.
"""

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock


log = logging.getLogger("brickshooter.game")

MAX_ENTRIES_PER_DIFFICULTY = 50
MAX_NAME_LENGTH = 24


@dataclass
class ScoreEntry:
    name: str
    score: int
    level: int
    difficulty: str
    date: str  #!< ISO 8601 UTC, second precision


class ScoreBoard:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._lock = Lock()
        self._entries: list[ScoreEntry] = []
        self._load()

    def record(self, *, name: str, score: int, level: int, difficulty: str) -> ScoreEntry | None:
        """Append a finished-game record. No-op if score is zero or negative."""
        if score <= 0:
            return None
        entry = ScoreEntry(
            name=_sanitize_name(name),
            score=int(score),
            level=int(level),
            difficulty=str(difficulty),
            date=_utc_iso_now(),
        )
        with self._lock:
            self._entries.append(entry)
            self._trim_locked()
            self._save_locked()
        log.info(
            "SCOREBOARD recorded name=%s score=%d level=%d difficulty=%s",
            entry.name, entry.score, entry.level, entry.difficulty,
        )
        return entry

    def top(self, *, difficulty: str, limit: int = 10) -> list[ScoreEntry]:
        with self._lock:
            entries = [e for e in self._entries if e.difficulty == difficulty]
        entries.sort(key=_score_key, reverse=True)
        return entries[:limit]

    # --- internals -----------------------------------------------------

    def _load(self) -> None:
        if not self._path.exists():
            return
        try:
            raw = self._path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if not isinstance(data, list):
                raise ValueError("scores file root is not a list")
            self._entries = [ScoreEntry(**e) for e in data]
        except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
            corrupt = self._path.with_suffix(self._path.suffix + ".corrupt")
            try:
                self._path.replace(corrupt)
            except OSError:
                pass
            log.warning("scores file unreadable (%s); moved aside to %s", exc, corrupt)
            self._entries = []

    def _trim_locked(self) -> None:
        by_diff: dict[str, list[ScoreEntry]] = {}
        for e in self._entries:
            by_diff.setdefault(e.difficulty, []).append(e)
        out: list[ScoreEntry] = []
        for entries in by_diff.values():
            entries.sort(key=_score_key, reverse=True)
            out.extend(entries[:MAX_ENTRIES_PER_DIFFICULTY])
        self._entries = out

    def _save_locked(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_suffix(self._path.suffix + ".tmp")
        payload = json.dumps([asdict(e) for e in self._entries], separators=(",", ":"))
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, self._path)


def _sanitize_name(name: str) -> str:
    cleaned = (name or "").strip()
    if not cleaned:
        return "Anonymous"
    return cleaned[:MAX_NAME_LENGTH]


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _score_key(entry: ScoreEntry) -> tuple[int, str]:
    # Tie-break by date (earlier wins) so repeat wins don't displace older
    # records of the same score.
    return (entry.score, -ord(entry.date[0]) if entry.date else 0)
