"""Gemini adapter over the `google-genai` SDK (PLAN.md D2: free tier by default)."""

import re
from collections.abc import AsyncIterator, Iterator, Sequence
from contextlib import contextmanager
from typing import Any, ClassVar

import httpx
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, ValidationError

from app.providers.errors import (
    ProviderAuthError,
    ProviderError,
    ProviderQuotaError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from app.providers.llm.base import (
    GenerationOptions,
    JsonResult,
    LLMProvider,
    Message,
    ReasoningEffort,
    StreamEvent,
    TextDelta,
    Usage,
)

# Gemini 3 can't switch thinking off; "minimal" is its floor (and Flash-Lite's default).
THINKING_LEVELS: dict[ReasoningEffort, types.ThinkingLevel] = {
    "none": types.ThinkingLevel.MINIMAL,
    "low": types.ThinkingLevel.LOW,
    "medium": types.ThinkingLevel.MEDIUM,
    "high": types.ThinkingLevel.HIGH,
}

# 429 is deliberately not retried: on the free tier it usually means the quota is
# spent, and the caller should fall back (to Ollama) instead of waiting.
RETRY_STATUS_CODES = [408, 500, 502, 503, 504]


class GeminiProvider(LLMProvider):
    name: ClassVar[str] = "gemini"

    def __init__(
        self, *, api_key: str | None = None, timeout_s: float = 60.0, client: Any = None
    ) -> None:
        # `client` lets tests inject a stub with the same `.aio.models` surface.
        self._client = client or genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=int(timeout_s * 1000),  # milliseconds
                retry_options=types.HttpRetryOptions(
                    attempts=3, http_status_codes=RETRY_STATUS_CODES
                ),
            ),
        )

    async def stream_chat(
        self,
        model_id: str,
        *,
        system: str,
        messages: Sequence[Message],
        options: GenerationOptions,
    ) -> AsyncIterator[StreamEvent]:
        config = _config(system, options)
        usage: types.GenerateContentResponseUsageMetadata | None = None
        with _translate_errors():
            stream = await self._client.aio.models.generate_content_stream(
                model=model_id, contents=_contents(messages), config=config
            )
            async for chunk in stream:
                if chunk.usage_metadata is not None:
                    usage = chunk.usage_metadata  # cumulative; the last one wins
                if chunk.text:
                    yield TextDelta(chunk.text)
        yield _usage(model_id, usage)

    async def complete_json[T: BaseModel](
        self,
        model_id: str,
        *,
        system: str,
        messages: Sequence[Message],
        schema: type[T],
        options: GenerationOptions,
    ) -> JsonResult[T]:
        config = _config(system, options)
        config.response_mime_type = "application/json"
        config.response_json_schema = schema.model_json_schema()
        with _translate_errors():
            response = await self._client.aio.models.generate_content(
                model=model_id, contents=_contents(messages), config=config
            )
        try:
            value = schema.model_validate_json(response.text or "")
        except ValidationError as exc:
            raise ProviderResponseError(self.name, f"response did not match schema: {exc}") from exc
        return JsonResult(value=value, usage=_usage(model_id, response.usage_metadata))

    async def aclose(self) -> None:
        await self._client.aio.aclose()


def _contents(messages: Sequence[Message]) -> list[types.Content]:
    return [
        types.Content(
            role="model" if m.role == "assistant" else "user", parts=[types.Part(text=m.content)]
        )
        for m in messages
    ]


def _config(system: str, options: GenerationOptions) -> types.GenerateContentConfig:
    config = types.GenerateContentConfig(
        system_instruction=system,
        temperature=options.temperature,
        max_output_tokens=options.max_output_tokens,
    )
    if options.reasoning_effort is not None:
        config.thinking_config = types.ThinkingConfig(
            thinking_level=THINKING_LEVELS[options.reasoning_effort]
        )
    return config


def _usage(model_id: str, meta: types.GenerateContentResponseUsageMetadata | None) -> Usage:
    if meta is None:
        return Usage(model=f"gemini:{model_id}", input_tokens=0, output_tokens=0)
    return Usage(
        model=f"gemini:{model_id}",
        input_tokens=meta.prompt_token_count or 0,
        output_tokens=meta.candidates_token_count or 0,
        thinking_tokens=meta.thoughts_token_count or 0,
    )


@contextmanager
def _translate_errors() -> Iterator[None]:
    try:
        yield
    except errors.APIError as exc:
        raise _from_api_error(exc) from exc
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise ProviderUnavailableError("gemini", f"network error: {exc!r}") from exc


def _from_api_error(exc: errors.APIError) -> ProviderError:
    message = exc.message or str(exc)
    if exc.code == 429:
        return ProviderQuotaError("gemini", message, retry_after_s=_retry_delay(exc.details))
    if exc.code in (401, 403):
        return ProviderAuthError("gemini", f"{message} (check GEMINI_API_KEY)")
    if exc.code in (400, 404):
        return ProviderRequestError("gemini", message)
    return ProviderUnavailableError("gemini", f"HTTP {exc.code}: {message}")


def _retry_delay(details: Any) -> float | None:
    """Read google.rpc.RetryInfo ("retryDelay": "17s") from a 429 body, if present."""
    error = details.get("error", {}) if isinstance(details, dict) else {}
    for item in error.get("details", []) or []:
        if isinstance(item, dict) and item.get("@type", "").endswith("google.rpc.RetryInfo"):
            match = re.fullmatch(r"(\d+(?:\.\d+)?)s", str(item.get("retryDelay", "")))
            if match:
                return float(match.group(1))
    return None
