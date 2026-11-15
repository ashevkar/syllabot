import logging
from collections.abc import AsyncIterator, Sequence

from pydantic import BaseModel

from app.providers.errors import ProviderQuotaError, ProviderUnavailableError
from app.providers.llm.base import (
    ChatModel,
    GenerationOptions,
    JsonResult,
    Message,
    StreamEvent,
    TextDelta,
)
from app.providers.model_ref import ModelRef

logger = logging.getLogger(__name__)

# Worth retrying elsewhere. Auth and bad-request errors are not: they'd fail the same way
# next time and should surface.
FALLBACK_ON = (ProviderQuotaError, ProviderUnavailableError)


class FallbackChatModel:
    """Uses `primary`; switches to `fallback` on quota/outage errors (Gemini → Ollama).

    A stream only falls back if the primary failed before sending any text, so a
    student never sees half an answer from one model glued to another.
    """

    def __init__(self, primary: ChatModel, fallback: ChatModel) -> None:
        self._primary = primary
        self._fallback = fallback

    @property
    def ref(self) -> ModelRef:
        return self._primary.ref

    async def stream_chat(
        self,
        *,
        system: str,
        messages: Sequence[Message],
        options: GenerationOptions | None = None,
    ) -> AsyncIterator[StreamEvent]:
        sent_text = False
        try:
            async for event in self._primary.stream_chat(
                system=system, messages=messages, options=options
            ):
                sent_text = sent_text or isinstance(event, TextDelta)
                yield event
            return
        except FALLBACK_ON as exc:
            if sent_text:
                raise
            self._log(exc)
        async for event in self._fallback.stream_chat(
            system=system, messages=messages, options=options
        ):
            yield event

    async def complete_json[T: BaseModel](
        self,
        *,
        system: str,
        messages: Sequence[Message],
        schema: type[T],
        options: GenerationOptions | None = None,
    ) -> JsonResult[T]:
        try:
            return await self._primary.complete_json(
                system=system, messages=messages, schema=schema, options=options
            )
        except FALLBACK_ON as exc:
            self._log(exc)
        return await self._fallback.complete_json(
            system=system, messages=messages, schema=schema, options=options
        )

    def _log(self, exc: Exception) -> None:
        logger.warning("LLM fallback %s -> %s: %s", self._primary.ref, self._fallback.ref, exc)
