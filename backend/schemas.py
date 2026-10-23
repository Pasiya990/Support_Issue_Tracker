"""Pydantic request and response schemas."""

from datetime import datetime
from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Priority(str, Enum):
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class IssueStatus(str, Enum):
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    RESOLVED = "Resolved"


def clean_required_text(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("This field cannot be empty.")
    return value


def clean_optional_text(value: object) -> object:
    if not isinstance(value, str):
        return value
    return value.strip() or None


class IssueCreate(BaseModel):
    client_name: Annotated[str, Field(min_length=1, max_length=200)]
    issue_title: Annotated[str, Field(min_length=1, max_length=250)]
    description: Annotated[str, Field(min_length=1)]
    assigned_engineer: Annotated[str | None, Field(max_length=200)] = None
    priority: Priority = Priority.MEDIUM
    status: IssueStatus = IssueStatus.OPEN

    @field_validator("client_name", "issue_title", "description", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return clean_required_text(value) if isinstance(value, str) else value

    @field_validator("assigned_engineer", mode="before")
    @classmethod
    def trim_engineer(cls, value: object) -> object:
        return clean_optional_text(value)

    @model_validator(mode="after")
    def resolved_issue_needs_engineer(self):
        if self.status == IssueStatus.RESOLVED and not self.assigned_engineer:
            raise ValueError("Select an assigned engineer before resolving an issue.")
        return self


class IssueUpdate(BaseModel):
    client_name: Annotated[str, Field(min_length=1, max_length=200)]
    issue_title: Annotated[str, Field(min_length=1, max_length=250)]
    description: Annotated[str, Field(min_length=1)]
    assigned_engineer: Annotated[str | None, Field(max_length=200)] = None
    priority: Priority
    status: IssueStatus

    @field_validator("client_name", "issue_title", "description", mode="before")
    @classmethod
    def trim_text(cls, value: object) -> object:
        return clean_required_text(value) if isinstance(value, str) else value

    @field_validator("assigned_engineer", mode="before")
    @classmethod
    def trim_engineer(cls, value: object) -> object:
        return clean_optional_text(value)

    @model_validator(mode="after")
    def resolved_issue_needs_engineer(self):
        if self.status == IssueStatus.RESOLVED and not self.assigned_engineer:
            raise ValueError("Select an assigned engineer before resolving an issue.")
        return self


class StatusUpdate(BaseModel):
    status: IssueStatus


class IssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    issue_id: int
    client_name: str
    issue_title: str
    description: str
    assigned_engineer: str | None
    priority: Priority
    status: IssueStatus
    date_time_reported: datetime
    is_overdue_high_priority: bool


class IssueStats(BaseModel):
    total_issues: int
    open_issues: int
    in_progress_issues: int
    resolved_issues: int
    high_priority_issues: int
    overdue_high_priority_issues: int
