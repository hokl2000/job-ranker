"""Unit tests for check_job_log.py, using the three made-up rows from the lesson.

Run: python test_check_job_log.py
"""
import tempfile
from pathlib import Path

from check_job_log import check_count, check_rows, read_rows

LOG = """# Job log
## Log
| Sent | Job | Employer | Link / ID | Deadline | Status |
|---|---|---|---|---|---|
| 2026-10-19 | Old job | KU | https://example.dk/1 | unknown (checked 2026-10-26) | applied (2026-10-20) |
| 2026-11-02 | Dataanalytiker | Region H | https://www.jobindex.dk/vis-job/h1710001 | 2026-11-20 | sent |
| 2026-11-02 | IT-projektleder | Aarhus Kommune | jobindex h1710002 | 20. nov | sent |
| 2026-11-02 | Forretningsanalytiker | Skattestyrelsen | https://www.jobindex.dk/vis-job/h1710003 | unknown | applied (2026-11-02) |
"""


def problems_for(row_number: int) -> list[str]:
    return [p for p in check_rows(read_rows(LOG)) if p.startswith(f"Row {row_number} ")]


def test_reads_four_rows() -> None:
    assert len(read_rows(LOG)) == 4


def test_good_row_and_old_applied_row_pass() -> None:
    assert problems_for(1) == []  # 'applied' is fine on a row from an older run
    assert problems_for(2) == []


def test_row_two_breaks_link_and_deadline() -> None:
    problems = problems_for(3)
    assert len(problems) == 2
    assert any("link" in p for p in problems) and any("deadline" in p for p in problems)


def test_row_three_breaks_status_rule() -> None:
    problems = problems_for(4)
    assert len(problems) == 1 and "only 'sent'" in problems[0]


def test_deleted_rows_are_caught() -> None:
    with tempfile.TemporaryDirectory() as folder:
        count_file = Path(folder) / "count.txt"
        assert check_count(10, count_file) == []   # first check: nothing to compare with
        assert check_count(12, count_file) == []   # rows added: fine
        assert len(check_count(11, count_file)) == 1  # one row gone: caught


if __name__ == "__main__":
    test_reads_four_rows()
    test_good_row_and_old_applied_row_pass()
    test_row_two_breaks_link_and_deadline()
    test_row_three_breaks_status_rule()
    test_deleted_rows_are_caught()
    print("OK - all 5 job-log check tests passed")
