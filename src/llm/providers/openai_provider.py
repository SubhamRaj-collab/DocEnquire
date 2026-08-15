from collections.abc import AsyncIterator

from src.llm.base import LLMProvider, LLMResponse


class OpenAILLMProvider(LLMProvider):
    def __init__(
        self,
        model: str = "gpt-4o",
        api_key: str | None = None,
        azure_endpoint: str | None = None,
    ):
        raise NotImplementedError(
            "OpenAI provider not yet implemented. Install `openai` and add to [project.optional-dependencies]."
        )

    async def generate(self, prompt: str, **kwargs) -> LLMResponse:
        raise NotImplementedError

    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        raise NotImplementedError
        yield  # noqa: unreachable

    def model_name(self) -> str:
        raise NotImplementedError
