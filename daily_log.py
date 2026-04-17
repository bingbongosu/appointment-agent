from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path


REPORTS_DIR = Path("reports")
HEADERS = ["timestamp", "process", "comment"]


def get_daily_log_filename(date: datetime | None = None) -> str:
    """
    Returns filename in format: DailyLogDDMMYYYY.csv
    """
    date = date or datetime.now()
    return f"DailyLog{date.strftime('%d%m%Y')}.csv"

def daily_log_exists(
    reports_dir: Path | str = REPORTS_DIR,
    date: datetime | None = None
) -> bool:
    """
    Returns True if the daily log file exists, otherwise False.
    """
    reports_dir = Path(reports_dir)
    filename = get_daily_log_filename(date)
    file_path = reports_dir / filename
    return file_path.exists()


def create_daily_log(
    reports_dir: Path | str = REPORTS_DIR,
    date: datetime | None = None
) -> Path:
    """
    Creates the daily log file if it does not exist.
    If it already exists, it leaves it alone.

    Returns the path to the daily log file.
    """
    reports_dir = Path(reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    filename = get_daily_log_filename(date)
    file_path = reports_dir / filename

    if not file_path.exists():
        with file_path.open(mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(HEADERS)

    return file_path

def log_report_entry(
    comment: str,
    process_name: str = "unknown_process",
    reports_dir: Path | str = REPORTS_DIR,
    timestamp: datetime | None = None
) -> Path:
    """
    Appends a timestamped entry to the current day's log file.

    Returns the path to the file written to.
    """
    if not comment or not comment.strip():
        raise ValueError("comment must not be empty")

    now = timestamp or datetime.now()
    file_path = create_daily_log(reports_dir=reports_dir, date=now)

    with file_path.open(mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([
            now.isoformat(timespec="seconds"),
            process_name,
            comment.strip()
        ])

    return file_path