"""Database models."""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class SupportIssue(Base):
    __tablename__ = "support_issues"

    issue_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    client_name: Mapped[str] = mapped_column(String(200), nullable=False)
    issue_title: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, default="Medium")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Open")
    # SQLite does not preserve timezone metadata; services normalize loaded values to UTC.
    date_time_reported: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    assigned_engineer: Mapped[str | None] = mapped_column(String(200), nullable=True)
