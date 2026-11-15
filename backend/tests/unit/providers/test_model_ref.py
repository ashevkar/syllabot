import pytest

from app.providers.model_ref import ModelRef

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("value", "provider", "model_id"),
    [
        ("gemini:gemini-3.5-flash-lite", "gemini", "gemini-3.5-flash-lite"),
        ("ollama:qwen3:8b", "ollama", "qwen3:8b"),  # only the first colon splits
        (" fake:any ", "fake", "any"),
    ],
)
def test_parse(value: str, provider: str, model_id: str) -> None:
    ref = ModelRef.parse(value)
    assert (ref.provider, ref.model_id) == (provider, model_id)
    assert str(ref) == value.strip()


@pytest.mark.parametrize(
    ("value", "message"),
    [
        ("gemini-3.5-flash-lite", "provider:model_id"),
        ("gemini:", "provider:model_id"),
        ("openai:gpt-6-luna", "unknown provider 'openai'"),
    ],
)
def test_parse_rejects(value: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        ModelRef.parse(value)
