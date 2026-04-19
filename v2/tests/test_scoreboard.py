"""ScoreBoard: JSON file persistence, top-N per difficulty, atomic writes."""

import json

import pytest

from backend.scoreboard import MAX_ENTRIES_PER_DIFFICULTY, ScoreBoard


@pytest.fixture
def sb_path(tmp_path):
    return tmp_path / "scores.json"


class TestEmpty:
    def test_missing_file_returns_empty_top(self, sb_path):
        sb = ScoreBoard(sb_path)
        assert sb.top(difficulty="normal") == []


class TestRecord:
    def test_record_persists_to_disk(self, sb_path):
        sb1 = ScoreBoard(sb_path)
        sb1.record(name="Dad", score=950, level=5, difficulty="normal")

        # Fresh instance reads the file.
        sb2 = ScoreBoard(sb_path)
        top = sb2.top(difficulty="normal")
        assert len(top) == 1
        assert top[0].name == "Dad"
        assert top[0].score == 950
        assert top[0].level == 5

    def test_top_sorted_descending(self, sb_path):
        sb = ScoreBoard(sb_path)
        sb.record(name="A", score=100, level=1, difficulty="normal")
        sb.record(name="B", score=500, level=3, difficulty="normal")
        sb.record(name="C", score=250, level=2, difficulty="normal")
        scores = [e.score for e in sb.top(difficulty="normal")]
        assert scores == [500, 250, 100]

    def test_difficulties_kept_separate(self, sb_path):
        sb = ScoreBoard(sb_path)
        sb.record(name="easy-player", score=1000, level=10, difficulty="easy")
        sb.record(name="hard-player", score=500, level=5, difficulty="hard")
        assert len(sb.top(difficulty="easy")) == 1
        assert len(sb.top(difficulty="hard")) == 1
        assert sb.top(difficulty="normal") == []

    def test_zero_or_negative_score_rejected(self, sb_path):
        sb = ScoreBoard(sb_path)
        assert sb.record(name="x", score=0, level=1, difficulty="normal") is None
        assert sb.record(name="x", score=-50, level=1, difficulty="normal") is None
        assert sb.top(difficulty="normal") == []

    def test_name_sanitized(self, sb_path):
        sb = ScoreBoard(sb_path)
        sb.record(name="   ", score=100, level=1, difficulty="normal")
        assert sb.top(difficulty="normal")[0].name == "Anonymous"

    def test_name_truncated(self, sb_path):
        sb = ScoreBoard(sb_path)
        sb.record(name="a" * 100, score=100, level=1, difficulty="normal")
        assert len(sb.top(difficulty="normal")[0].name) == 24


class TestTrimming:
    def test_per_difficulty_cap(self, sb_path):
        sb = ScoreBoard(sb_path)
        for i in range(MAX_ENTRIES_PER_DIFFICULTY + 10):
            sb.record(name=f"p{i}", score=i + 1, level=1, difficulty="normal")
        # Re-read to make sure the cap survived a disk round-trip.
        sb2 = ScoreBoard(sb_path)
        all_normal = sb2.top(difficulty="normal", limit=1000)
        assert len(all_normal) == MAX_ENTRIES_PER_DIFFICULTY
        # Lowest scores dropped; only top-N kept.
        assert all_normal[-1].score == 11  # i=10 was score 11, the 50th from top


class TestCorruptFile:
    def test_garbage_file_moved_aside(self, sb_path):
        sb_path.write_text("this is not JSON")
        sb = ScoreBoard(sb_path)
        # Start empty.
        assert sb.top(difficulty="normal") == []
        # Corrupt file renamed.
        assert sb_path.with_suffix(".json.corrupt").exists()
        # Fresh writes still work.
        sb.record(name="A", score=100, level=1, difficulty="normal")
        assert sb.top(difficulty="normal")[0].score == 100


class TestAtomicity:
    def test_tmp_file_not_left_behind_after_successful_write(self, sb_path):
        sb = ScoreBoard(sb_path)
        sb.record(name="A", score=100, level=1, difficulty="normal")
        tmp = sb_path.with_suffix(".json.tmp")
        assert not tmp.exists()
        # And the real file is valid JSON.
        json.loads(sb_path.read_text())
