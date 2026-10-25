"""Checks the weekly job agent's output: the rows it writes to the job log.

The agent is a scheduled Claude task, so its output varies; the rules below come from the job
log's own header and must hold every time, so Python can check them exactly.

Rules:
1. Sent is a date (YYYY-MM-DD).
2. Deadline is a date, "unknown" or "unknown (checked YYYY-MM-DD)".
3. Status starts with one of the allowed status words.
4. Rows sent on or after URL_RULE_FROM store the full ad URL (https://...).
5. Rows from the newest run (the newest Sent date) have status "sent" - only Holger sets the others.
6. No rows deleted: the log has at least as many rows as at the last check.

Usage: save a copy of the job log as job_log.md (private, in .gitignore), then
    python check_job_log.py
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).parent
LOG = HERE / "job_log.md"
COUNT_FILE = HERE / "job_log_count.txt"  # row count from the last check (private)
URL_RULE_FROM = "2026-10-14"             # full URLs required from the first run after 13 Oct

DATE = r"\d{4}-\d{2}-\d{2}"
DEADLINE = re.compile(rf"{DATE}|unknown|unknown \(checked {DATE}\)")
STATUS_WORDS = ["sent", "applied", "interview", "rejected", "no answer", "not interested", "expired"]


def read_rows(text: str) -> list[dict]:
    """The table rows under '## Log' as dicts: sent, job, employer, link, deadline, status."""
    rows = []
    in_log = False
    for line in text.splitlines():
        if line.startswith("## "):
            in_log = line.strip() == "## Log"
            continue
        if not in_log or not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6 or cells[0] in ("Sent", "") or set(cells[0]) <= {"-"}:
            continue  # header, separator line or a broken row (caught by the count below)
        rows.append(dict(zip(["sent", "job", "employer", "link", "deadline", "status"], cells)))
    return rows


def check_rows(rows: list[dict]) -> list[str]:
    """Rules 1-5. Returns one message per broken rule; an empty list means all passed."""
    problems = []
    dates = [row["sent"] for row in rows if re.fullmatch(DATE, row["sent"])]
    newest = max(dates) if dates else None
    for number, row in enumerate(rows, start=1):
        where = f"Row {number} ({row['sent']}, {row['job'][:40]})"
        if not re.fullmatch(DATE, row["sent"]):
            problems.append(f"{where}: Sent is not a YYYY-MM-DD date: {row['sent']!r}")
        if not DEADLINE.fullmatch(row["deadline"]):
            problems.append(f"{where}: deadline has the wrong format: {row['deadline']!r}")
        if not any(row["status"].startswith(word) for word in STATUS_WORDS):
            problems.append(f"{where}: unknown status: {row['status']!r}")
        if row["sent"] >= URL_RULE_FROM and not row["link"].startswith("https://"):
            problems.append(f"{where}: link is not a full URL: {row['link']!r}")
        if row["sent"] == newest and row["status"] != "sent":
            problems.append(f"{where}: newest run wrote status {row['status']!r}, only 'sent' is allowed")
    return problems


def check_count(count: int, count_file: Path = COUNT_FILE) -> list[str]:
    """Rule 6: compare with the count saved at the last check, then save the new count."""
    problems = []
    if count_file.exists():
        before = int(count_file.read_text().strip())
        if count < before:
            problems.append(f"Rows deleted: {before} at the last check, {count} now")
    count_file.write_text(str(count))
    return problems


def main() -> None:
    rows = read_rows(LOG.read_text(encoding="utf-8"))
    problems = check_rows(rows) + check_count(len(rows))
    print(f"{len(rows)} rows checked.")
    for problem in problems:
        print("  FAIL", problem)
    print("OK - all rules passed" if not problems else f"{len(problems)} problem(s) found")
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
