"""Reusable business rules for timestamps and overdue issue detection."""

from datetime import datetime, timedelta, timezone

from backend.models import SupportIssue


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def normalize_utc(value: datetime) -> datetime:
    """Interpret naive SQLite datetimes as UTC and normalize aware values."""
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_overdue_high_priority(issue: SupportIssue, now: datetime | None = None) -> bool:
    current_time = normalize_utc(now or utc_now())
    reported = normalize_utc(issue.date_time_reported)
    return (
        issue.priority == "High"
        and issue.status != "Resolved"
        and current_time - reported > timedelta(hours=24)
    )


def issue_response_data(issue: SupportIssue, now: datetime | None = None) -> dict:
    """Build a response dictionary with the dynamic overdue flag."""
    return {
        "issue_id": issue.issue_id,
        "client_name": issue.client_name,
        "issue_title": issue.issue_title,
        "description": issue.description,
        "priority": issue.priority,
        "status": issue.status,
        "date_time_reported": normalize_utc(issue.date_time_reported),
        "is_overdue_high_priority": is_overdue_high_priority(issue, now),
    }
