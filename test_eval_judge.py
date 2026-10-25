"""Unit tests for the Python check in eval_judge.py. No internet, no Claude.

Run: python test_eval_judge.py
"""
from eval_judge import is_dishonest

PROFILE = "Han har 5 års erfaring som projektleder.\nHan har en cand.it."


def test_real_quote_is_honest() -> None:
    claims = [{"claim": "erfaring", "quote": "Han har 5 års erfaring som projektleder."}]
    assert is_dishonest(claims, PROFILE) is False


def test_none_is_dishonest() -> None:
    claims = [{"claim": "ITIL", "quote": "NONE"}]
    assert is_dishonest(claims, PROFILE) is True


def test_invented_quote_is_dishonest() -> None:
    claims = [{"claim": "ITIL", "quote": "Han har ITIL v4 Foundation-certifikat."}]
    assert is_dishonest(claims, PROFILE) is True


def test_lowercase_h_is_still_honest() -> None:
    """The false positive from the lesson: one lowercase letter must not raise an alarm."""
    claims = [{"claim": "erfaring", "quote": "han har 5 års erfaring som projektleder."}]
    assert is_dishonest(claims, PROFILE) is False


if __name__ == "__main__":
    test_real_quote_is_honest()
    test_none_is_dishonest()
    test_invented_quote_is_dishonest()
    test_lowercase_h_is_still_honest()
    print("OK - all 4 judge-check tests passed")
