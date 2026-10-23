"""Database operations, kept separate from HTTP routes."""

from datetime import datetime, timedelta

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.models import SupportIssue
from backend.schemas import IssueCreate, IssueUpdate
from backend.services import is_overdue_high_priority, normalize_utc, utc_now


def create_issue(db: Session, issue_data: IssueCreate) -> SupportIssue:
    issue = SupportIssue(
        **issue_data.model_dump(mode="json"), date_time_reported=utc_now()
    )
    db.add(issue)
    db.commit()
    db.refresh(issue)
    return issue


def get_issue(db: Session, issue_id: int) -> SupportIssue | None:
    return db.get(SupportIssue, issue_id)


def list_issues(
    db: Session, *, skip: int = 0, limit: int = 100,
    q: str | None = None, priority: str | None = None, status: str | None = None,
) -> list[SupportIssue]:
    statement = select(SupportIssue)
    if q is not None:
        pattern = f"%{q}%"
        statement = statement.where(or_(
            func.lower(SupportIssue.client_name).like(func.lower(pattern)),
            func.lower(SupportIssue.issue_title).like(func.lower(pattern)),
        ))
    if priority is not None:
        statement = statement.where(SupportIssue.priority == priority)
    if status is not None:
        statement = statement.where(SupportIssue.status == status)
    statement = statement.order_by(SupportIssue.date_time_reported.desc(), SupportIssue.issue_id.desc())
    return list(db.scalars(statement.offset(skip).limit(limit)).all())


def update_issue(db: Session, issue: SupportIssue, values: IssueUpdate) -> SupportIssue:
    for field, value in values.model_dump(mode="json").items():
        setattr(issue, field, value)
    db.commit()
    db.refresh(issue)
    return issue


def update_status(db: Session, issue: SupportIssue, status: str) -> SupportIssue:
    issue.status = status
    db.commit()
    db.refresh(issue)
    return issue


def delete_issue(db: Session, issue: SupportIssue) -> None:
    db.delete(issue)
    db.commit()


def overdue_issues(db: Session, now: datetime | None = None) -> list[SupportIssue]:
    current = normalize_utc(now or utc_now())
    cutoff = current - timedelta(hours=24)
    statement = select(SupportIssue).where(
        SupportIssue.priority == "High",
        SupportIssue.status != "Resolved",
        SupportIssue.date_time_reported < cutoff.replace(tzinfo=None),
    ).order_by(SupportIssue.date_time_reported.asc())
    return list(db.scalars(statement).all())


def issue_statistics(db: Session, now: datetime | None = None) -> dict[str, int]:
    issues = list(db.scalars(select(SupportIssue)).all())
    current = now or utc_now()
    return {
        "total_issues": len(issues),
        "open_issues": sum(item.status == "Open" for item in issues),
        "in_progress_issues": sum(item.status == "In Progress" for item in issues),
        "resolved_issues": sum(item.status == "Resolved" for item in issues),
        "high_priority_issues": sum(item.priority == "High" for item in issues),
        "overdue_high_priority_issues": sum(
            is_overdue_high_priority(item, current) for item in issues
        ),
    }
