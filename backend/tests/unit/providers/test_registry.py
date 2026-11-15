import pytest

from app.config import ConfigError, Settings
from app.providers.llm.base import BoundChatModel
from app.providers.llm.fake import FakeLLM
from app.providers.llm.fallback import FallbackChatModel
from app.providers.llm.gemini import GeminiProvider
from app.providers.llm.ollama import OllamaProvider
from app.providers.registry import ProviderRegistry

pytestmark = pytest.mark.unit

BASE = {
    "database_url": "postgresql+asyncpg://u:p@localhost:5433/db",
    "redis_url": "redis://localhost:6379/0",
}


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, **{**BASE, **overrides})  # type: ignore[arg-type]


def test_gemini_without_key_fails_with_instructions() -> None:
    registry = ProviderRegistry(_settings(gemini_api_key=None))

    with pytest.raises(ConfigError, match=r"GEMINI_API_KEY is required.*aistudio"):
        registry.default_chat_model()


async def test_builds_each_provider_once_and_closes_them() -> None:
    registry = ProviderRegistry(_settings(gemini_api_key="test-key"))

    gemini = registry.llm_provider("gemini")
    assert isinstance(gemini, GeminiProvider)
    assert registry.llm_provider("gemini") is gemini
    assert isinstance(registry.llm_provider("ollama"), OllamaProvider)

    await registry.aclose()
    assert registry.llm_provider("gemini") is not gemini  # rebuilt after close


def test_default_chat_model_wraps_fallback_when_configured() -> None:
    registry = ProviderRegistry(
        _settings(default_chat_model="fake:primary", fallback_chat_model="fake:backup")
    )

    model = registry.default_chat_model()

    assert isinstance(model, FallbackChatModel)
    assert str(model.ref) == "fake:primary"


def test_no_fallback_wrapper_without_fallback_model() -> None:
    registry = ProviderRegistry(_settings(default_chat_model="fake:primary"))

    assert isinstance(registry.default_chat_model(), BoundChatModel)


def test_extraction_model_defaults_to_chat_model() -> None:
    registry = ProviderRegistry(_settings(default_chat_model="fake:chat"))

    assert str(registry.extraction_model().ref) == "fake:chat"


def test_registered_provider_is_used() -> None:
    fake = FakeLLM()
    registry = ProviderRegistry(_settings())
    registry.register("gemini", fake)  # no key needed when a provider is injected

    model = registry.chat_model("gemini:gemini-3.5-flash-lite")

    assert isinstance(model, BoundChatModel)
    assert registry.llm_provider("gemini") is fake


@pytest.mark.parametrize(
    ("field", "value"),
    [("default_chat_model", "gpt-6-luna"), ("judge_model", "openai:gpt-6.1-terra")],
)
def test_settings_reject_bad_model_strings(field: str, value: str) -> None:
    with pytest.raises(ValueError, match="provider"):
        _settings(**{field: value})


def test_blank_optional_settings_mean_unset() -> None:
    settings = _settings(gemini_api_key="", fallback_chat_model=" ", extraction_model="")

    assert settings.gemini_api_key is None
    assert settings.fallback_chat_model is None
    assert settings.extraction_model is None
