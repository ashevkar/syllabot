from collections.abc import AsyncIterator

from app.providers.llm.base import ChatModel, Message, StreamEvent, TextDelta, Usage

SYSTEM = "Answer only from the syllabus."
HISTORY = [
    Message("user", "When is the midterm?"),
    Message("assistant", "Thursday Oct 15."),
    Message("user", "Where?"),
]


async def collect(stream: AsyncIterator[StreamEvent]) -> tuple[str, list[Usage]]:
    """Join text deltas; return them with every Usage seen (the contract says exactly one, last)."""
    text, usages, events = [], [], []
    async for event in stream:
        events.append(event)
        if isinstance(event, TextDelta):
            text.append(event.text)
        else:
            usages.append(event)
    assert events and isinstance(events[-1], Usage), "stream must end with a Usage event"
    return "".join(text), usages


async def stream_text(model: ChatModel) -> tuple[str, Usage]:
    text, usages = await collect(model.stream_chat(system=SYSTEM, messages=HISTORY))
    assert len(usages) == 1
    return text, usages[0]
