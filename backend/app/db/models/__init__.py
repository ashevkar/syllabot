"""All ORM models. Importing this package registers every table on `Base.metadata`."""

from app.db.models.bot import Bot, BotCollaborator
from app.db.models.chat import ChatMessage, ChatSession
from app.db.models.chunk import EMBEDDING_DIM, Chunk
from app.db.models.document import Document
from app.db.models.evals import EvalCase, EvalResult, EvalRun
from app.db.models.schedule import ScheduleItem
from app.db.models.template import Template
from app.db.models.user import User

__all__ = [
    "EMBEDDING_DIM",
    "Bot",
    "BotCollaborator",
    "ChatMessage",
    "ChatSession",
    "Chunk",
    "Document",
    "EvalCase",
    "EvalResult",
    "EvalRun",
    "ScheduleItem",
    "Template",
    "User",
]
