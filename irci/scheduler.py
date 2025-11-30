# irci/scheduler.py
"""
Scheduled analysis configuration for IRCI.

This module handles scheduling configuration storage.
Actual execution requires external triggers (GitHub Actions, cron, etc.)

For now, this stores user preferences and provides webhook endpoints
that can be triggered externally.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, List

from .logging import get_logger

log = get_logger("irci.scheduler")

SCHEDULES_FILE = Path(os.getenv("IRCI_SCHEDULES_FILE", ".cache/irci/schedules.json"))


def save_schedule(
    name: str,
    tickers: List[str],
    quarters: List[str],
    email: str,
    frequency: str = "weekly",
    enabled: bool = True
) -> Dict:
    """
    Save a scheduled analysis configuration.

    Args:
        name: Schedule name/identifier
        tickers: List of ticker symbols
        quarters: List of quarters to analyze
        email: Email to send reports to
        frequency: 'daily', 'weekly', 'monthly'
        enabled: Whether schedule is active

    Returns:
        The saved schedule configuration
    """
    schedules = load_schedules()

    schedule = {
        "name": name,
        "tickers": tickers,
        "quarters": quarters,
        "email": email,
        "frequency": frequency,
        "enabled": enabled,
        "created_at": datetime.now().isoformat(),
        "last_run": None
    }

    schedules[name] = schedule

    # Save to file
    SCHEDULES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SCHEDULES_FILE, 'w') as f:
        json.dump(schedules, f, indent=2)

    log.info(f"Saved schedule: {name}")
    return schedule


def load_schedules() -> Dict:
    """Load all saved schedules."""
    if not SCHEDULES_FILE.exists():
        return {}

    try:
        with open(SCHEDULES_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        log.warning(f"Could not load schedules: {e}")
        return {}


def delete_schedule(name: str) -> bool:
    """Delete a schedule by name."""
    schedules = load_schedules()
    if name in schedules:
        del schedules[name]
        with open(SCHEDULES_FILE, 'w') as f:
            json.dump(schedules, f, indent=2)
        return True
    return False


def get_schedule(name: str) -> Optional[Dict]:
    """Get a specific schedule by name."""
    schedules = load_schedules()
    return schedules.get(name)


def update_last_run(name: str) -> None:
    """Update the last_run timestamp for a schedule."""
    schedules = load_schedules()
    if name in schedules:
        schedules[name]["last_run"] = datetime.now().isoformat()
        with open(SCHEDULES_FILE, 'w') as f:
            json.dump(schedules, f, indent=2)


def get_due_schedules() -> List[Dict]:
    """
    Get schedules that are due to run.

    Returns schedules based on their frequency and last_run time.
    """
    from datetime import timedelta

    schedules = load_schedules()
    due = []

    now = datetime.now()

    for name, schedule in schedules.items():
        if not schedule.get("enabled", True):
            continue

        last_run = schedule.get("last_run")
        if last_run:
            last_run_dt = datetime.fromisoformat(last_run)
        else:
            last_run_dt = datetime.min

        frequency = schedule.get("frequency", "weekly")

        if frequency == "daily":
            threshold = timedelta(hours=23)
        elif frequency == "weekly":
            threshold = timedelta(days=6)
        elif frequency == "monthly":
            threshold = timedelta(days=29)
        else:
            threshold = timedelta(days=7)

        if now - last_run_dt >= threshold:
            due.append(schedule)

    return due


def generate_cron_expression(frequency: str) -> str:
    """
    Generate a cron expression for the given frequency.

    Returns:
        Cron expression string
    """
    if frequency == "daily":
        return "0 8 * * *"  # 8 AM daily
    elif frequency == "weekly":
        return "0 8 * * 1"  # 8 AM every Monday
    elif frequency == "monthly":
        return "0 8 1 * *"  # 8 AM on the 1st of each month
    else:
        return "0 8 * * 1"  # Default to weekly
