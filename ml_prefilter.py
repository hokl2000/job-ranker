"""A cheap pre-filter: predicts from the job TITLE alone whether an ad is worth sending to rank_job.py.

Pipeline: find_jobs.py -> ml_prefilter.py (title only, free, instant) -> rank_job.py (Claude, full ad).
rank_job.py is unchanged; this only decides which ads it should score.

Training data: labels.csv from make_labels.py (Claude's title-only scores).
Label 1 = title score at or above LABEL_LINE. The full-ad 70+ line does not fit title-only
scores (only 1 of 96 titles reached 70); jobs that scored 70+ on the full ad got 55-65 from
their titles, so the line is 55.

Model: TF-IDF on the words of the title + logistic regression (scikit-learn).
"""
import csv
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import confusion_matrix, precision_score, recall_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline, make_pipeline

HERE = Path(__file__).parent
LABELS = HERE / "labels.csv"
LABEL_LINE = 55              # title score >= this -> label 1
THRESHOLDS = [0.5, 0.4, 0.3]  # probability lines to compare on the test set
TEST_SHARE = 0.25            # a quarter of the titles are kept back for testing
SEED = 42                    # fixed, so the split is the same every run


def load_labels(path: Path = LABELS) -> tuple[list[str], list[int]]:
    """Read titles and turn each score into a label (1 if score >= LABEL_LINE)."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    titles = [row["title"] for row in rows]
    labels = [1 if int(row["score"]) >= LABEL_LINE else 0 for row in rows]
    return titles, labels


def build_model() -> Pipeline:
    """TF-IDF turns titles into numbers; logistic regression learns one weight per word.
    class_weight='balanced' gives the rarer label more weight, so it isn't ignored."""
    return make_pipeline(
        TfidfVectorizer(lowercase=True),
        LogisticRegression(class_weight="balanced", max_iter=1000),
    )


def evaluate(true: list[int], probabilities: list[float], threshold: float) -> dict:
    """Compare the model with Claude's labels at one probability line."""
    predicted = [1 if p >= threshold else 0 for p in probabilities]
    tn, fp, fn, tp = confusion_matrix(true, predicted, labels=[0, 1]).ravel()
    return {
        "threshold": threshold,
        "tp": int(tp), "fp": int(fp), "fn": int(fn), "tn": int(tn),
        "recall": recall_score(true, predicted, zero_division=0),
        "precision": precision_score(true, predicted, zero_division=0),
        "passed": int(tp + fp),  # titles the pre-filter would send on to rank_job.py
    }


def top_words(model: Pipeline, n: int = 8) -> tuple[list, list]:
    """The words with the most positive and most negative model weights."""
    words = model.named_steps["tfidfvectorizer"].get_feature_names_out()
    weights = model.named_steps["logisticregression"].coef_[0]
    pairs = sorted(zip(weights, words))
    return pairs[-n:][::-1], pairs[:n]


def main() -> None:
    titles, labels = load_labels()
    print(f"{len(titles)} titles: {sum(labels)} with label 1 (score >= {LABEL_LINE}), "
          f"{len(labels) - sum(labels)} with label 0.")

    train_x, test_x, train_y, test_y = train_test_split(
        titles, labels, test_size=TEST_SHARE, stratify=labels, random_state=SEED
    )
    print(f"Train: {len(train_x)} titles. Test: {len(test_x)} titles "
          f"({sum(test_y)} with label 1).\n")

    model = build_model()
    model.fit(train_x, train_y)
    probabilities = model.predict_proba(test_x)[:, 1]

    print("Test set, model vs Claude:")
    for threshold in THRESHOLDS:
        r = evaluate(test_y, probabilities, threshold)
        print(f"  line {r['threshold']}: recall {r['recall']:.0%}, precision {r['precision']:.0%}, "
              f"passed {r['passed']} of {len(test_y)}  "
              f"(TP {r['tp']}, FP {r['fp']}, FN {r['fn']}, TN {r['tn']})")

    positive, negative = top_words(model)
    print("\nWords pointing to label 1:", ", ".join(f"{w} {v:+.2f}" for v, w in positive))
    print("Words pointing to label 0:", ", ".join(f"{w} {v:+.2f}" for v, w in negative))


if __name__ == "__main__":
    main()
