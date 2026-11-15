"""Opt-in smoke tests against real providers: `make test-live` (or `pytest -m live`).

They read the repo-root `.env`, use a few free-tier requests, and skip themselves when
a provider isn't configured or running.
"""

from collections.abc import AsyncIterator

import httpx
import pytest
from pydantic import BaseModel

from app.config import load_settings
from app.providers.llm.base import ChatModel, GenerationOptions, Message
from app.providers.registry import ProviderRegistry
from tests.unit.providers.helpers import collect

pytestmark = pytest.mark.live

SYSTEM = "You are a terse assistant. Answer in at most five words."
QUESTION = [Message("user", "What is the capital of France?")]


class Capital(BaseModel):
    city: str
    country: str


@pytest.fixture
async def registry() -> AsyncIterator[ProviderRegistry]:
    reg = ProviderRegistry(load_settings())
    yield reg
    await reg.aclose()


@pytest.fixture
def gemini(registry: ProviderRegistry) -> ChatModel:
    settings = load_settings()
    if settings.gemini_api_key is None:
        pytest.skip("GEMINI_API_KEY not set in .env")
    return registry.chat_model(settings.default_chat_model)


@pytest.fixture
def ollama(registry: ProviderRegistry) -> ChatModel:
    settings = load_settings()
    model = settings.fallback_chat_model or "ollama:qwen3:8b"
    if not model.startswith("ollama:"):
        pytest.skip("FALLBACK_CHAT_MODEL is not an Ollama model")
    try:
        httpx.get(f"{settings.ollama_base_url}/api/version", timeout=2).raise_for_status()
    except httpx.HTTPError:
        pytest.skip(f"Ollama not running at {settings.ollama_base_url}")
    return registry.chat_model(model)


async def _smoke(model: ChatModel) -> None:
    options = GenerationOptions(reasoning_effort="none", max_output_tokens=256)
    text, usages = await collect(
        model.stream_chat(system=SYSTEM, messages=QUESTION, options=options)
    )
    assert "paris" in text.lower()
    assert usages[0].input_tokens > 0
    assert usages[0].output_tokens > 0

    result = await model.complete_json(
        system="Extract the answer as JSON.", messages=QUESTION, schema=Capital, options=options
    )
    assert result.value.city.lower() == "paris"


async def test_gemini_streams_and_returns_json(gemini: ChatModel) -> None:
    await _smoke(gemini)


async def test_ollama_streams_and_returns_json(ollama: ChatModel) -> None:
    await _smoke(ollama)
