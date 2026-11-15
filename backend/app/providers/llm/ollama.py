"""Ollama adapter: the free, private, unmetered backup (PLAN.md D2)."""

from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import contextmanager
from typing import Any, ClassVar

import httpx
from ollama import AsyncClient, ResponseError
from pydantic import BaseModel, ValidationError

from app.providers.errors import (
    ProviderRequestError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from app.providers.llm.base import (
    GenerationOptions,
    JsonResult,
    LLMProvider,
    Message,
    StreamEvent,
    TextDelta,
    Usage,
)


class OllamaProvider(LLMProvider):
    name: ClassVar[str] = "ollama"

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        timeout_s: float = 120.0,
        client: Any = None,
    ) -> None:
        self._base_url = base_url
        self._client = client or AsyncClient(host=base_url, timeout=timeout_s)

    async def stream_chat(
        self,
        model_id: str,
        *,
        system: str,
        messages: Sequence[Message],
        options: GenerationOptions,
    ) -> AsyncIterator[StreamEvent]:
        usage = Usage(model=f"ollama:{model_id}", input_tokens=0, output_tokens=0)
        with self._translate_errors(model_id):
            stream = await self._client.chat(
                model=model_id,
                messages=_messages(system, messages),
                stream=True,
                **_kwargs(options),
            )
            async for part in stream:
                if part.message.content:
                    yield TextDelta(part.message.content)
                if part.done:
                    usage = _usage(model_id, part)
        yield usage

    async def complete_json[T: BaseModel](
        self,
        model_id: str,
        *,
        system: str,
        messages: Sequence[Message],
        schema: type[T],
        options: GenerationOptions,
    ) -> JsonResult[T]:
        with self._translate_errors(model_id):
            response = await self._client.chat(
                model=model_id,
                messages=_messages(system, messages),
                format=schema.model_json_schema(),
                **_kwargs(options),
            )
        try:
            value = schema.model_validate_json(response.message.content or "")
        except ValidationError as exc:
            raise ProviderResponseError(self.name, f"response did not match schema: {exc}") from exc
        return JsonResult(value=value, usage=_usage(model_id, response))

    @contextmanager
    def _translate_errors(self, model_id: str) -> Iterator[None]:
        try:
            yield
        except ConnectionError as exc:
            raise ProviderUnavailableError(
                self.name, f"Ollama is not reachable at {self._base_url}; is it running?"
            ) from exc
        except httpx.TimeoutException as exc:
            raise ProviderUnavailableError(self.name, "request timed out") from exc
        except ResponseError as exc:
            if exc.status_code == 404:
                raise ProviderRequestError(
                    self.name, f"model {model_id!r} not found; run `ollama pull {model_id}`"
                ) from exc
            if exc.status_code >= 500 or exc.status_code == -1:
                raise ProviderUnavailableError(self.name, exc.error) from exc
            raise ProviderRequestError(self.name, exc.error) from exc


def _messages(system: str, messages: Sequence[Message]) -> list[dict[str, str]]:
    return [{"role": "system", "content": system}] + [
        {"role": m.role, "content": m.content} for m in messages
    ]


def _kwargs(options: GenerationOptions) -> dict[str, Any]:
    kwargs: dict[str, Any] = {}
    model_options: dict[str, Any] = {}
    if options.temperature is not None:
        model_options["temperature"] = options.temperature
    if options.max_output_tokens is not None:
        model_options["num_predict"] = options.max_output_tokens
    if model_options:
        kwargs["options"] = model_options
    if options.reasoning_effort is not None:
        # Qwen3 thinks by default, which is slow on CPU; "none" turns it off.
        kwargs["think"] = options.reasoning_effort != "none"
    return kwargs


def _usage(model_id: str, response: Any) -> Usage:
    return Usage(
        model=f"ollama:{model_id}",
        input_tokens=response.prompt_eval_count or 0,
        output_tokens=response.eval_count or 0,  # Ollama counts thinking tokens in here
    )
