"""REST endpoints for support issue management."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response, status
from sqlalchemy.orm import Session

from backend import crud
from backend.database import get_db
from backend.schemas import IssueCreate, IssueResponse, IssueStats, IssueStatus, IssueUpdate, Priority, StatusUpdate
from backend.services import issue_response_data

router = APIRouter(prefix="/api/issues", tags=["issues"])
DbSession = Annotated[Session, Depends(get_db)]
IssueId = Annotated[int, Path(gt=0)]


def require_issue(db: Session, issue_id: int):
    issue = crud.get_issue(db, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail=f"Issue {issue_id} was not found.")
    return issue


@router.post("", response_model=IssueResponse, status_code=status.HTTP_201_CREATED)
def create_support_issue(payload: IssueCreate, db: DbSession):
    return issue_response_data(crud.create_issue(db, payload))


# Declare static paths before /{issue_id} so names like "search" are never parsed as IDs.
@router.get("/search", response_model=list[IssueResponse])
def search_issues(
    db: DbSession,
    q: Annotated[str, Query(min_length=1, max_length=200)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    assigned_engineer: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
):
    query = q.strip()
    if not query:
        raise HTTPException(status_code=422, detail="Search query cannot be empty.")
    engineer = assigned_engineer.strip() if assigned_engineer is not None else None
    if assigned_engineer is not None and not engineer:
        raise HTTPException(status_code=422, detail="Assigned engineer cannot be blank.")
    return [issue_response_data(item) for item in crud.list_issues(
        db, q=query, skip=skip, limit=limit, assigned_engineer=engineer
    )]


@router.get("/filter", response_model=list[IssueResponse])
def filter_issues(
    db: DbSession,
    priority: Priority | None = None,
    status_filter: Annotated[IssueStatus | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    assigned_engineer: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
):
    query = q.strip() if q is not None else None
    if query == "":
        raise HTTPException(status_code=422, detail="Search query cannot be empty.")
    engineer = assigned_engineer.strip() if assigned_engineer is not None else None
    if assigned_engineer is not None and not engineer:
        raise HTTPException(status_code=422, detail="Assigned engineer cannot be blank.")
    return [issue_response_data(item) for item in crud.list_issues(
        db, q=query, priority=priority.value if priority else None,
        status=status_filter.value if status_filter else None, skip=skip, limit=limit,
        assigned_engineer=engineer,
    )]


@router.get("/overdue", response_model=list[IssueResponse])
def get_overdue_issues(db: DbSession):
    return [issue_response_data(item) for item in crud.overdue_issues(db)]


@router.get("/stats", response_model=IssueStats)
def get_issue_statistics(db: DbSession):
    return crud.issue_statistics(db)


@router.get("", response_model=list[IssueResponse])
def get_issues(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 100,
    q: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
    priority: Priority | None = None,
    status_filter: Annotated[IssueStatus | None, Query(alias="status")] = None,
    assigned_engineer: Annotated[str | None, Query(min_length=1, max_length=200)] = None,
):
    query = q.strip() if q is not None else None
    if query == "":
        raise HTTPException(status_code=422, detail="Search query cannot be empty.")
    engineer = assigned_engineer.strip() if assigned_engineer is not None else None
    if assigned_engineer is not None and not engineer:
        raise HTTPException(status_code=422, detail="Assigned engineer cannot be blank.")
    return [issue_response_data(item) for item in crud.list_issues(
        db, skip=skip, limit=limit, q=query,
        priority=priority.value if priority else None,
        status=status_filter.value if status_filter else None,
        assigned_engineer=engineer,
    )]


@router.get("/{issue_id}", response_model=IssueResponse)
def get_issue(issue_id: IssueId, db: DbSession):
    return issue_response_data(require_issue(db, issue_id))


@router.put("/{issue_id}", response_model=IssueResponse)
def replace_issue(issue_id: IssueId, payload: IssueUpdate, db: DbSession):
    issue = require_issue(db, issue_id)
    return issue_response_data(crud.update_issue(db, issue, payload))


@router.patch("/{issue_id}/status", response_model=IssueResponse)
def change_issue_status(issue_id: IssueId, payload: StatusUpdate, db: DbSession):
    issue = require_issue(db, issue_id)
    if payload.status == IssueStatus.RESOLVED and not issue.assigned_engineer:
        raise HTTPException(
            status_code=422,
            detail="Select an assigned engineer before resolving this issue.",
        )
    return issue_response_data(crud.update_status(db, issue, payload.status.value))


@router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_issue(issue_id: IssueId, db: DbSession):
    crud.delete_issue(db, require_issue(db, issue_id))
    return Response(status_code=status.HTTP_204_NO_CONTENT)
