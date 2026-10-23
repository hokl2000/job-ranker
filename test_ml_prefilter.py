"""Unit tests for ml_prefilter.py. No internet, no Claude, no labels.csv needed.

Run: python test_ml_prefilter.py
"""
import tempfile
from pathlib import Path

import ml_prefilter as mp


def test_load_labels_uses_the_line() -> None:
    """A score exactly at LABEL_LINE gives 1, one point below gives 0."""
    line = mp.LABEL_LINE
    text = f"title;score;label\nA;{line - 1};0\nB;{line};0\nC;80;1\n"
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "labels.csv"
        path.write_text(text, encoding="utf-8")
        titles, labels = mp.load_labels(path)
    assert titles == ["A", "B", "C"]
    assert labels == [0, 1, 1]  # the old label column is ignored; the score decides


def test_evaluate_counts() -> None:
    """Known case: one of each in the confusion matrix."""
    true = [1, 1, 0, 0]
    probabilities = [0.9, 0.2, 0.6, 0.1]
    r = mp.evaluate(true, probabilities, threshold=0.5)
    assert (r["tp"], r["fn"], r["fp"], r["tn"]) == (1, 1, 1, 1)
    assert r["recall"] == 0.5 and r["precision"] == 0.5
    assert r["passed"] == 2


def test_lower_line_never_lowers_recall() -> None:
    """Moving the probability line down can only keep or raise recall."""
    true = [1, 1, 1, 0, 0]
    probabilities = [0.8, 0.45, 0.35, 0.6, 0.2]
    recalls = [mp.evaluate(true, probabilities, t)["recall"] for t in (0.5, 0.4, 0.3)]
    assert recalls == sorted(recalls)


def test_model_learns_obvious_words() -> None:
    """Trained on clear examples, the model ranks a new IT title above a new non-IT title."""
    titles = ["it projektleder", "digital projektleder", "it konsulent",
              "elektriker", "tømrer", "pædagog"] * 3
    labels = [1, 1, 1, 0, 0, 0] * 3
    model = mp.build_model()
    model.fit(titles, labels)
    good, bad = model.predict_proba(["it projektleder kommune", "elektriker kommune"])[:, 1]
    assert good > bad


if __name__ == "__main__":
    test_load_labels_uses_the_line()
    test_evaluate_counts()
    test_lower_line_never_lowers_recall()
    test_model_learns_obvious_words()
    print("OK - all 4 ml_prefilter tests passed")
