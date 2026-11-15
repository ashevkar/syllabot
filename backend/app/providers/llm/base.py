"""The provider-neutral LLM interface (NFR-13).

Callers never import an SDK: they get a `ChatModel` from the registry and consume
`stream_chat()` events or `complete_json()` results.
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Sequence
from dataclasses import dataclass
from typing import ClassVar, Literal, Protocol

from pydantic import BaseModel

from app.providers.model_ref import ModelRef

Role = Literal["user", "assistant"]
ReasoningEffort = Literal["none", "low", "medium", "high"]


@dataclass(frozen=True)
class Message:
    role: Role
    content: str


@dataclass(frozen=True)
class GenerationOptions:
    """Per-call knobs. `None` means "provider default"."""

    temperature: float | None = None
    # How much the model may think before answering. "none" is the lowest the
    # model supports (Gemini 3 bottoms out at "minimal"). PLAN.md D3.
    reasoning_effort: ReasoningEffort | None = None
    max_output_tokens: int | None = None


@dataclass(frozen=True)
class TextDelta:
    text: str


@dataclass(frozen=True)
class Usage:
    model: str  # the `provider:model_id` that actually answered (may be the fallback)
    input_tokens: int
    output_tokens: int  # visible answer tokens
    thinking_tokens: int = 0  # billed like output tokens where the provider reports them


StreamEvent = TextDelta | Usage


@dataclass(frozen=True)
class JsonResult[T: BaseModel]:
    value: T
    usage: Usage


class LLMProvider(ABC):
    """One adapter per provider SDK. Stateless apart from its client."""

    name: ClassVar[str]

    @abstractmethod
    def stream_chat(
        self,
        model_id: str,
        *,
        system: str,
        messages: Sequence[Message],
        options: GenerationOptions,
    ) -> AsyncIterator[StreamEvent]:
        """Yield `TextDelta`s, then exactly one `Usage` as the last event."""

    @abstractmethod
    async def complete_json[T: BaseModel](
        self,
        model_id: str,
        *,
        system: str,
        messages: Sequence[Message],
        schema: type[T],
        options: GenerationOptions,
    ) -> JsonResult[T]:
        """Ask for output matching `schema` and return it validated."""

    async def aclose(self) -> None:  # noqa: B027  (optional hook, default no-op)
        """Release network clients."""


class ChatModel(Protocol):
    """A model bound to its provider; what services receive from the registry."""

    @property
    def ref(self) -> ModelRef: ...

    def stream_chat(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        options: GenerationOptions | None = None,
    ) -> AsyncIterator[StreamEvent]: ...

    async def complete_json[T: BaseModel](
        self,
        *,
        system: str,
        messages: Sequence[Message],
        schema: type[T],
        options: GenerationOptions | None = None,
    ) -> JsonResult[T]: ...


class BoundChatModel:
    """`ChatModel` for a single provider + model id."""

    def __init__(self, provider: LLMProvider, ref: ModelRef) -> None:
        self._provider = provider
        self._ref = ref

    @property
    def ref(self) -> ModelRef:
        return self._ref

    def stream_chat(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        options: GenerationOptions | None = None,
    ) -> AsyncIterator[StreamEvent]:
        return self._provider.stream_chat(
            self._ref.model_id,
            system=system,
            messages=messages,
            options=options or GenerationOptions(),
        )

    async def complete_json[T: BaseModel](
        self,
        *,
        system: str,
        messages: Sequence[Message],
        schema: type[T],
        options: GenerationOptions | None = None,
    ) -> JsonResult[T]:
        return await self._provider.complete_json(
            self._ref.model_id,
            system=system,
            messages=messages,
            schema=schema,
            options=options or GenerationOptions(),
        )
