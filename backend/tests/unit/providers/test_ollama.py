from collections.abc import AsyncIterator
from typing import Any

import pytest
from ollama import ChatResponse, Message, ResponseError
from pydantic import BaseModel

from app.providers.errors import (
    ProviderRequestError,
    ProviderResponseError,
    ProviderUnavailableError,
)
from app.providers.llm.base import BoundChatModel, GenerationOptions
from app.providers.llm.ollama import OllamaProvider
from app.providers.model_ref import ModelRef
from tests.unit.providers.helpers import HISTORY, SYSTEM, collect, stream_text

pytestmark = pytest.mark.unit

MODEL = ModelRef.parse("ollama:qwen3:8b")


def _part(content: str, *, done: bool = False, prompt: int = 0, out: int = 0) -> ChatResponse:
    return ChatResponse(
        model="qwen3:8b",
        message=Message(role="assistant", content=content),
        done=done,
        prompt_eval_count=prompt if done else None,
        eval_count=out if done else None,
    )


class StubClient:
    """Mimics `ollama.AsyncClient.chat` for both streaming and one-shot calls."""

    def __init__(self, *, parts: list[ChatResponse] | None = None, error: Exception | None = None):
        self.parts = parts or []
        self.error = error
        self.requests: list[dict[str, Any]] = []

    async def chat(self, **request: Any) -> Any:
        self.requests.append(request)
        if self.error:
            raise self.error
        if not request.get("stream"):
            return self.parts[0]

        async def gen() -> AsyncIterator[ChatResponse]:
            for part in self.parts:
                yield part

        return gen()


def _model(stub: StubClient) -> BoundChatModel:
    return BoundChatModel(OllamaProvider(client=stub), MODEL)


async def test_stream_yields_text_then_usage() -> None:
    stub = StubClient(parts=[_part("ENG "), _part("101."), _part("", done=True, prompt=80, out=5)])

    text, usage = await stream_text(_model(stub))

    assert text == "ENG 101."
    assert (usage.model, usage.input_tokens, usage.output_tokens) == ("ollama:qwen3:8b", 80, 5)


async def test_request_puts_system_first_and_maps_options() -> None:
    stub = StubClient(parts=[_part("ok", done=True)])
    options = GenerationOptions(temperature=0.1, reasoning_effort="none", max_output_tokens=200)

    await collect(_model(stub).stream_chat(system=SYSTEM, messages=HISTORY, options=options))

    request = stub.requests[0]
    assert request["model"] == "qwen3:8b"
    assert [m["role"] for m in request["messages"]] == ["system", "user", "assistant", "user"]
    assert request["messages"][0]["content"] == SYSTEM
    assert request["options"] == {"temperature": 0.1, "num_predict": 200}
    assert request["think"] is False


async def test_unset_options_are_not_sent() -> None:
    stub = StubClient(parts=[_part("ok", done=True)])

    await stream_text(_model(stub))

    assert "options" not in stub.requests[0]
    assert "think" not in stub.requests[0]


async def test_not_running_is_unavailable() -> None:
    stub = StubClient(error=ConnectionError("Failed to connect to Ollama"))

    with pytest.raises(ProviderUnavailableError, match="not reachable"):
        await stream_text(_model(stub))


async def test_missing_model_tells_you_to_pull_it() -> None:
    stub = StubClient(error=ResponseError("model 'qwen3:8b' not found", 404))

    with pytest.raises(ProviderRequestError, match="ollama pull qwen3:8b"):
        await stream_text(_model(stub))


class Deadline(BaseModel):
    title: str


async def test_complete_json_passes_schema_as_format() -> None:
    stub = StubClient(parts=[_part('{"title": "HW1"}', done=True, prompt=30, out=6)])

    result = await _model(stub).complete_json(system=SYSTEM, messages=HISTORY, schema=Deadline)

    assert result.value == Deadline(title="HW1")
    assert result.usage.output_tokens == 6
    assert stub.requests[0]["format"] == Deadline.model_json_schema()


async def test_complete_json_rejects_bad_json() -> None:
    stub = StubClient(parts=[_part("not json", done=True)])

    with pytest.raises(ProviderResponseError):
        await _model(stub).complete_json(system=SYSTEM, messages=HISTORY, schema=Deadline)
