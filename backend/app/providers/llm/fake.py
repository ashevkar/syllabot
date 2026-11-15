"""Deterministic in-memory provider for tests and offline development (`fake:<anything>`)."""

from collections import deque
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass, field
from typing import ClassVar

from pydantic import BaseModel

from app.providers.llm.base import (
    GenerationOptions,
    JsonResult,
    LLMProvider,
    Message,
    StreamEvent,
    TextDelta,
    Usage,
)


@dataclass
class FakeCall:
    method: str
    model_id: str
    system: str
    messages: list[Message]
    options: GenerationOptions
    schema: type[BaseModel] | None = None


@dataclass
class FakeLLM(LLMProvider):
    """Replies are consumed in order; with none queued, it echoes the last user message.

    Queue an `Exception` instead of a reply to make the next call raise it.
    """

    name: ClassVar[str] = "fake"

    replies: deque[str | Exception] = field(default_factory=deque)
    json_replies: deque[BaseModel | Exception] = field(default_factory=deque)
    calls: list[FakeCall] = field(default_factory=list)

    def queue(self, *replies: str | Exception) -> "FakeLLM":
        self.replies.extend(replies)
        return self

    def queue_json(self, *replies: BaseModel | Exception) -> "FakeLLM":
        self.json_replies.extend(replies)
        return self

    async def stream_chat(
        self,
        model_id: str,
        *,
        system: str,
        messages: Sequence[Message],
        options: GenerationOptions,
    ) -> AsyncIterator[StreamEvent]:
        self.calls.append(FakeCall("stream_chat", model_id, system, list(messages), options))
        reply = self.replies.popleft() if self.replies else _echo(messages)
        if isinstance(reply, Exception):
            raise reply
        words = reply.split(" ")
        for i, word in enumerate(words):
            yield TextDelta(word if i == len(words) - 1 else word + " ")
        yield _usage(model_id, system, messages, reply)

    async def complete_json[T: BaseModel](
        self,
        model_id: str,
        *,
        system: str,
        messages: Sequence[Message],
        schema: type[T],
        options: GenerationOptions,
    ) -> JsonResult[T]:
        self.calls.append(
            FakeCall("complete_json", model_id, system, list(messages), options, schema)
        )
        if not self.json_replies:
            raise AssertionError("FakeLLM.complete_json called with no queued json reply")
        reply = self.json_replies.popleft()
        if isinstance(reply, Exception):
            raise reply
        value = schema.model_validate(reply.model_dump())
        return JsonResult(
            value=value, usage=_usage(model_id, system, messages, value.model_dump_json())
        )


def _echo(messages: Sequence[Message]) -> str:
    last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
    return f"fake answer to: {last_user}"


def _usage(model_id: str, system: str, messages: Sequence[Message], reply: str) -> Usage:
    # Word counts stand in for tokens: deterministic and good enough for cost-math tests.
    prompt_words = len(system.split()) + sum(len(m.content.split()) for m in messages)
    return Usage(
        model=f"fake:{model_id}", input_tokens=prompt_words, output_tokens=len(reply.split())
    )
