from collections.abc import AsyncIterator
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
from google.genai import errors, types
from pydantic import BaseModel

from app.providers.errors import (
    ProviderAuthError,
    ProviderQuotaError,
    ProviderRequestError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from app.providers.llm.base import BoundChatModel, GenerationOptions
from app.providers.llm.gemini import GeminiProvider
from app.providers.model_ref import ModelRef
from tests.unit.providers.helpers import HISTORY, SYSTEM, collect, stream_text

pytestmark = pytest.mark.unit

MODEL = ModelRef.parse("gemini:gemini-3.5-flash-lite")


def _chunk(text: str | None, usage: dict[str, int] | None = None) -> types.GenerateContentResponse:
    parts = [types.Part(text=text)] if text is not None else []
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=parts))],
        usage_metadata=types.GenerateContentResponseUsageMetadata(**usage) if usage else None,
    )


class StubModels:
    """Mimics `client.aio.models`: records requests, replays chunks or raises."""

    def __init__(self, *, chunks: list[Any] | None = None, error: Exception | None = None) -> None:
        self.chunks = chunks or []
        self.error = error
        self.requests: list[dict[str, Any]] = []

    async def generate_content_stream(self, **request: Any) -> AsyncIterator[Any]:
        self.requests.append(request)
        if self.error:
            raise self.error

        async def gen() -> AsyncIterator[Any]:
            for chunk in self.chunks:
                if isinstance(chunk, Exception):
                    raise chunk
                yield chunk

        return gen()

    async def generate_content(self, **request: Any) -> Any:
        self.requests.append(request)
        if self.error:
            raise self.error
        return self.chunks[0]


def _model(stub: StubModels) -> BoundChatModel:
    client = SimpleNamespace(aio=SimpleNamespace(models=stub))
    return BoundChatModel(GeminiProvider(client=client), MODEL)


def _api_error(
    code: int, status: str, details: list[dict[str, Any]] | None = None
) -> errors.APIError:
    body = {"error": {"code": code, "message": f"{status} happened", "status": status}}
    if details:
        body["error"]["details"] = details
    cls = errors.ClientError if code < 500 else errors.ServerError
    return cls(code, body)


async def test_stream_yields_text_then_usage_including_thinking_tokens() -> None:
    stub = StubModels(
        chunks=[
            _chunk("ENG "),
            _chunk(None),  # empty chunks are skipped
            _chunk(
                "101.",
                {"prompt_token_count": 120, "candidates_token_count": 4, "thoughts_token_count": 9},
            ),
        ]
    )

    text, usage = await stream_text(_model(stub))

    assert text == "ENG 101."
    assert usage.model == "gemini:gemini-3.5-flash-lite"
    assert (usage.input_tokens, usage.output_tokens, usage.thinking_tokens) == (120, 4, 9)


async def test_request_maps_roles_system_and_options() -> None:
    stub = StubModels(chunks=[_chunk("ok")])
    model = _model(stub)
    options = GenerationOptions(temperature=0.2, reasoning_effort="none", max_output_tokens=256)

    await collect(model.stream_chat(system=SYSTEM, messages=HISTORY, options=options))

    request = stub.requests[0]
    assert request["model"] == "gemini-3.5-flash-lite"
    assert [c.role for c in request["contents"]] == ["user", "model", "user"]
    assert request["contents"][2].parts[0].text == "Where?"
    config: types.GenerateContentConfig = request["config"]
    assert config.system_instruction == SYSTEM
    assert config.temperature == 0.2
    assert config.max_output_tokens == 256
    assert config.thinking_config is not None
    assert config.thinking_config.thinking_level == types.ThinkingLevel.MINIMAL  # "none" → floor


async def test_unset_options_are_left_to_the_provider() -> None:
    stub = StubModels(chunks=[_chunk("ok")])

    await stream_text(_model(stub))

    config: types.GenerateContentConfig = stub.requests[0]["config"]
    assert config.temperature is None
    assert config.thinking_config is None


async def test_429_becomes_quota_error_with_retry_delay() -> None:
    retry = {"@type": "type.googleapis.com/google.rpc.RetryInfo", "retryDelay": "17s"}
    stub = StubModels(error=_api_error(429, "RESOURCE_EXHAUSTED", [retry]))

    with pytest.raises(ProviderQuotaError) as excinfo:
        await stream_text(_model(stub))

    assert excinfo.value.retry_after_s == 17.0
    assert excinfo.value.provider == "gemini"


async def test_error_raised_mid_stream_is_translated_too() -> None:
    stub = StubModels(chunks=[_chunk("Hel"), _api_error(503, "UNAVAILABLE")])

    with pytest.raises(ProviderUnavailableError, match="HTTP 503"):
        await stream_text(_model(stub))


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (_api_error(401, "UNAUTHENTICATED"), ProviderAuthError),
        (_api_error(403, "PERMISSION_DENIED"), ProviderAuthError),
        (_api_error(404, "NOT_FOUND"), ProviderRequestError),
        (_api_error(400, "INVALID_ARGUMENT"), ProviderRequestError),
        (_api_error(500, "INTERNAL"), ProviderUnavailableError),
        (httpx.ConnectTimeout("slow"), ProviderUnavailableError),
    ],
)
async def test_error_mapping(error: Exception, expected: type[Exception]) -> None:
    with pytest.raises(expected):
        await stream_text(_model(StubModels(error=error)))


class Deadline(BaseModel):
    title: str
    due: str


async def test_complete_json_sends_schema_and_validates() -> None:
    stub = StubModels(
        chunks=[
            _chunk(
                '{"title": "HW1", "due": "2026-09-04"}',
                {"prompt_token_count": 50, "candidates_token_count": 12},
            )
        ]
    )

    result = await _model(stub).complete_json(system=SYSTEM, messages=HISTORY, schema=Deadline)

    assert result.value == Deadline(title="HW1", due="2026-09-04")
    assert result.usage.input_tokens == 50
    config: types.GenerateContentConfig = stub.requests[0]["config"]
    assert config.response_mime_type == "application/json"
    assert config.response_json_schema == Deadline.model_json_schema()


async def test_complete_json_rejects_output_not_matching_schema() -> None:
    stub = StubModels(chunks=[_chunk('{"title": "HW1"}')])

    with pytest.raises(ProviderResponseError, match="did not match schema"):
        await _model(stub).complete_json(system=SYSTEM, messages=HISTORY, schema=Deadline)
