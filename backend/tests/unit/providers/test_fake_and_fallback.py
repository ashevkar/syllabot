import pytest
from pydantic import BaseModel

from app.providers.errors import (
    ProviderAuthError,
    ProviderQuotaError,
    ProviderUnavailableError,
)
from app.providers.llm.base import BoundChatModel, TextDelta
from app.providers.llm.fake import FakeLLM
from app.providers.llm.fallback import FallbackChatModel
from app.providers.model_ref import ModelRef
from tests.unit.providers.helpers import HISTORY, SYSTEM, stream_text

pytestmark = pytest.mark.unit


def _bound(provider: FakeLLM, name: str) -> BoundChatModel:
    return BoundChatModel(provider, ModelRef.parse(f"fake:{name}"))


class Item(BaseModel):
    title: str


async def test_fake_echoes_and_records_calls() -> None:
    fake = FakeLLM()

    text, usage = await stream_text(_bound(fake, "m"))

    assert text == "fake answer to: Where?"
    assert usage.model == "fake:m"
    assert usage.output_tokens == 4
    assert fake.calls[0].system == SYSTEM
    assert fake.calls[0].messages == HISTORY


async def test_fake_replays_queued_replies_and_errors() -> None:
    fake = FakeLLM().queue("first reply", ProviderQuotaError("fake", "quota"))
    model = _bound(fake, "m")

    assert (await stream_text(model))[0] == "first reply"
    with pytest.raises(ProviderQuotaError):
        await stream_text(model)


async def test_fake_complete_json() -> None:
    fake = FakeLLM().queue_json(Item(title="HW1"))

    result = await _bound(fake, "m").complete_json(system=SYSTEM, messages=HISTORY, schema=Item)

    assert result.value == Item(title="HW1")


@pytest.mark.parametrize(
    "error", [ProviderQuotaError("fake", "quota"), ProviderUnavailableError("fake", "down")]
)
async def test_fallback_used_when_primary_fails_before_any_text(error: Exception) -> None:
    primary, backup = FakeLLM().queue(error), FakeLLM().queue("from backup")
    model = FallbackChatModel(_bound(primary, "primary"), _bound(backup, "backup"))

    text, usage = await stream_text(model)

    assert text == "from backup"
    assert usage.model == "fake:backup"  # usage reports who actually answered


async def test_no_fallback_once_text_was_sent() -> None:
    class FailsMidStream(FakeLLM):
        async def stream_chat(self, model_id, *, system, messages, options):
            yield TextDelta("half an ans")
            raise ProviderQuotaError("fake", "quota")

    backup = FakeLLM()
    model = FallbackChatModel(_bound(FailsMidStream(), "primary"), _bound(backup, "backup"))

    with pytest.raises(ProviderQuotaError):
        await stream_text(model)
    assert backup.calls == []


async def test_auth_errors_are_not_masked_by_fallback() -> None:
    primary = FakeLLM().queue(ProviderAuthError("fake", "bad key"))
    backup = FakeLLM()
    model = FallbackChatModel(_bound(primary, "primary"), _bound(backup, "backup"))

    with pytest.raises(ProviderAuthError):
        await stream_text(model)
    assert backup.calls == []


async def test_fallback_for_complete_json() -> None:
    primary = FakeLLM().queue_json(ProviderQuotaError("fake", "quota"))
    backup = FakeLLM().queue_json(Item(title="from backup"))
    model = FallbackChatModel(_bound(primary, "primary"), _bound(backup, "backup"))

    result = await model.complete_json(system=SYSTEM, messages=HISTORY, schema=Item)

    assert result.value.title == "from backup"
