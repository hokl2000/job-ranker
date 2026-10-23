"""Makes labels.csv: Claude scores job TITLES only (no ad text), for training ml_prefilter.py.

Titles come from titles_joblog.txt (one per line) and the 'title' column of jobs_found.csv.
Each title is scored once with rank_job.py. label = 1 if the score is 70 or more, else 0.
Titles already in labels.csv are skipped, so you can stop the script and start it again.
"""
import csv
from pathlib import Path

from rank_job import rank_job

HERE = Path(__file__).parent
LABELS = HERE / "labels.csv"
THRESHOLD = 70
TITLE_ONLY_NOTE = "(Kun jobtitlen er kendt, ikke selve opslaget.) "


def key(title: str) -> str:
    """Same key for titles that differ only in dash type, upper/lower case or spaces."""
    return " ".join(title.replace("–", "-").lower().split())


def detect_delimiter(first_line: str) -> str:
    """Pick the separator that appears most often in the header line."""
    return max([";", "\t", ","], key=first_line.count)


def read_titles() -> list[str]:
    """All titles from both sources, duplicates removed (the first spelling is kept)."""
    titles = []

    joblog = HERE / "titles_joblog.txt"
    if joblog.exists():
        lines = joblog.read_text(encoding="utf-8").splitlines()
        titles += [line.strip() for line in lines if line.strip()]

    found = HERE / "jobs_found.csv"
    if found.exists():
        with open(found, encoding="utf-8-sig", newline="") as f:
            delimiter = detect_delimiter(f.readline())
            f.seek(0)
            for row in csv.DictReader(f, delimiter=delimiter):
                title = (row.get("title") or "").strip()
                if title:
                    titles.append(title)

    unique = {}
    for title in titles:
        unique.setdefault(key(title), title)
    return list(unique.values())


def already_scored() -> set[str]:
    """Keys of the titles already in labels.csv."""
    if not LABELS.exists():
        return set()
    with open(LABELS, encoding="utf-8-sig", newline="") as f:
        return {key(row["title"]) for row in csv.DictReader(f, delimiter=";")}


def main() -> None:
    titles = read_titles()
    done = already_scored()
    todo = [title for title in titles if key(title) not in done]
    print(f"{len(titles)} titles, {len(done)} already scored, {len(todo)} to score now.")

    new_file = not LABELS.exists()
    with open(LABELS, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f, delimiter=";")
        if new_file:
            writer.writerow(["title", "score", "label"])
        for number, title in enumerate(todo, start=1):
            print(f"Scoring {number} of {len(todo)}: {title[:60]}")
            try:
                answer = rank_job(TITLE_ONLY_NOTE + title)
            except Exception as error:  # e.g. claude -p printed nothing; skip and go on
                print(f"   skipped ({error})")
                continue
            label = 1 if answer["score"] >= THRESHOLD else 0
            writer.writerow([title, answer["score"], label])
            f.flush()  # saved now, so a crash loses at most one title

    with open(LABELS, encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f, delimiter=";"))
    positives = sum(1 for row in rows if row["label"] == "1")
    print(f"Done. labels.csv has {len(rows)} titles: {positives} at 70+ (label 1), "
          f"{len(rows) - positives} below 70 (label 0).")


if __name__ == "__main__":
    main()
