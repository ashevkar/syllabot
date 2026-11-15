from dataclasses import dataclass
from typing import Literal, cast, get_args

ProviderName = Literal["gemini", "ollama", "fake"]
PROVIDERS: tuple[str, ...] = get_args(ProviderName)


@dataclass(frozen=True)
class ModelRef:
    """A model named as `provider:model_id`, e.g. `gemini:gemini-3.5-flash-lite`.

    Only the first colon separates the provider, so Ollama tags like
    `ollama:qwen3:8b` keep their own colon.
    """

    provider: ProviderName
    model_id: str

    @classmethod
    def parse(cls, value: str) -> "ModelRef":
        provider, sep, model_id = value.strip().partition(":")
        if not sep or not model_id:
            raise ValueError(f"model must look like 'provider:model_id', got {value!r}")
        if provider not in PROVIDERS:
            raise ValueError(
                f"unknown provider {provider!r} in {value!r}; expected one of {PROVIDERS}"
            )
        return cls(cast(ProviderName, provider), model_id)

    def __str__(self) -> str:
        return f"{self.provider}:{self.model_id}"
