"""Turns `provider:model_id` strings into ready-to-use models (NFR-13)."""

from app.config import ConfigError, Settings
from app.providers.llm.base import BoundChatModel, ChatModel, LLMProvider
from app.providers.llm.fake import FakeLLM
from app.providers.llm.fallback import FallbackChatModel
from app.providers.llm.gemini import GeminiProvider
from app.providers.llm.ollama import OllamaProvider
from app.providers.model_ref import ModelRef, ProviderName


class ProviderRegistry:
    """Owns one client per provider, created on first use and closed on shutdown.

    Lazy creation means the API starts without a Gemini key (health checks, Ollama-only
    setups); the missing key is reported when a Gemini model is first used.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._llm: dict[ProviderName, LLMProvider] = {}

    def register(self, name: ProviderName, provider: LLMProvider) -> None:
        """Install a provider instance directly (tests, custom setups)."""
        self._llm[name] = provider

    def llm_provider(self, name: ProviderName) -> LLMProvider:
        if name not in self._llm:
            self._llm[name] = self._build(name)
        return self._llm[name]

    def chat_model(self, model: str, *, fallback: str | None = None) -> ChatModel:
        primary = self._bind(model)
        if fallback is None or fallback == model:
            return primary
        return FallbackChatModel(primary, self._bind(fallback))

    def default_chat_model(self) -> ChatModel:
        return self.chat_model(
            self._settings.default_chat_model, fallback=self._settings.fallback_chat_model
        )

    def judge_model(self) -> ChatModel:
        return self.chat_model(self._settings.judge_model)

    def extraction_model(self) -> ChatModel:
        return self.chat_model(
            self._settings.extraction_model or self._settings.default_chat_model,
            fallback=self._settings.fallback_chat_model,
        )

    async def aclose(self) -> None:
        for provider in self._llm.values():
            await provider.aclose()
        self._llm.clear()

    def _bind(self, model: str) -> ChatModel:
        ref = ModelRef.parse(model)
        return BoundChatModel(self.llm_provider(ref.provider), ref)

    def _build(self, name: ProviderName) -> LLMProvider:
        s = self._settings
        match name:
            case "gemini":
                if s.gemini_api_key is None:
                    raise ConfigError(
                        "GEMINI_API_KEY is required for gemini:* models. Get a free key at "
                        "https://aistudio.google.com/apikey and put it in .env."
                    )
                return GeminiProvider(
                    api_key=s.gemini_api_key.get_secret_value(), timeout_s=s.llm_timeout_s
                )
            case "ollama":
                return OllamaProvider(base_url=s.ollama_base_url, timeout_s=s.llm_timeout_s * 2)
            case "fake":
                return FakeLLM()
