from collections.abc import AsyncIterator

from src.llm.base import LLMProvider, LLMResponse


class ClaudeLLMProvider(LLMProvider):
    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str | None = None):
        raise NotImplementedError(
            "Claude provider not yet implemented. Install `anthropic` and add to [project.optional-dependencies]."
        )

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        raise NotImplementedError

    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        raise NotImplementedError
        yield  # noqa: unreachable

    def model_name(self) -> str:
        raise NotImplementedError
