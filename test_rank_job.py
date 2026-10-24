"""Unit tests for the Python parts of rank_job.py. No internet, no Claude.

subprocess.run (the `claude -p` call) is replaced by a fake that returns a scripted answer,
so only Python's own work is tested: adding up the parts and the transport-0 deal-breaker.

Run: python test_rank_job.py
"""
import json
from types import SimpleNamespace
from unittest.mock import patch

import rank_job


def fake_claude(parts: dict) -> SimpleNamespace:
    """What `claude -p --output-format json` would print, with the given part-scores."""
    output = {"is_error": False, "structured_output": dict(parts, why="test")}
    return SimpleNamespace(stdout=json.dumps(output))


def score_with(parts: dict) -> dict:
    """Run rank_job() with the fake Claude answer instead of a real call."""
    with patch("rank_job.subprocess.run", return_value=fake_claude(parts)):
        return rank_job.rank_job("any ad")


def test_python_adds_up_the_parts() -> None:
    answer = score_with({"krav": 30, "erfaringsniveau": 20, "spor": 15, "transport": 10, "andet": 5})
    assert answer["score"] == 80


def test_transport_zero_gives_total_zero() -> None:
    answer = score_with({"krav": 40, "erfaringsniveau": 20, "spor": 15, "transport": 0, "andet": 10})
    assert answer["score"] == 0  # unreachable = deal-breaker, even with every other part at max


def test_claude_error_raises() -> None:
    error = SimpleNamespace(stdout=json.dumps({"is_error": True, "result": "login expired"}))
    with patch("rank_job.subprocess.run", return_value=error):
        try:
            rank_job.rank_job("any ad")
        except RuntimeError:
            return
    raise AssertionError("expected RuntimeError")


if __name__ == "__main__":
    test_python_adds_up_the_parts()
    test_transport_zero_gives_total_zero()
    test_claude_error_raises()
    print("OK - all 3 rank_job tests passed")
