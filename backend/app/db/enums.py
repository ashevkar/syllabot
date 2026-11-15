"""Python mirrors of the Postgres enum types in docs/database-schema.md §2."""

from enum import StrEnum
from typing import Any

from sqlalchemy import Enum


class UserRole(StrEnum):
    ADMIN = "admin"
    INSTRUCTOR = "instructor"


class BotStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"  # unused in v1 (PLAN.md D9)


class CollabLevel(StrEnum):
    EDITOR = "editor"
    VIEWER = "viewer"  # unused in v1 (PLAN.md D9)


class DocStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class DocSource(StrEnum):
    FILE = "file"
    URL = "url"


class ScheduleKind(StrEnum):
    ASSIGNMENT = "assignment"
    EXAM = "exam"
    QUIZ = "quiz"
    PROJECT = "project"
    READING = "reading"
    HOLIDAY = "holiday"
    OTHER = "other"


class MessageRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"


class EvalVerdict(StrEnum):
    PASS = "pass"  # noqa: S105  (a verdict, not a password)
    PARTIAL = "partial"
    FAIL = "fail"
    ERROR = "error"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


def pg_enum(enum_cls: type[StrEnum], name: str) -> Enum:
    """Native Postgres enum that stores the lowercase values, not the member names."""
    return Enum(enum_cls, name=name, values_callable=_values)


def _values(enum_cls: type[Any]) -> list[str]:
    return [member.value for member in enum_cls]
