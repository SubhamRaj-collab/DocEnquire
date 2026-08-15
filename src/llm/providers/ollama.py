from collections.abc import AsyncIterator

from langchain_ollama import ChatOllama, OllamaEmbeddings

from src.llm.base import EmbeddingProvider, LLMProvider, LLMResponse


class OllamaLLMProvider(LLMProvider):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "gemma2:2b",
        timeout: float = 120.0,
    ):
        self._model = model
        self._llm = ChatOllama(
            base_url=base_url,
            model=model,
            timeout=timeout,
        )

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> LLMResponse:
        self._llm.temperature = temperature
        self._llm.num_predict = max_tokens

        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("human", prompt))

        result = await self._llm.ainvoke(messages)

        usage = None
        if hasattr(result, "usage_metadata") and result.usage_metadata:
            usage = {
                "prompt_tokens": result.usage_metadata.get("input_tokens", 0),
                "completion_tokens": result.usage_metadata.get("output_tokens", 0),
            }

        return LLMResponse(
            text=result.content,
            model=self._model,
            usage=usage,
        )

    async def stream(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        self._llm.temperature = temperature
        self._llm.num_predict = max_tokens

        messages = []
        if system_prompt:
            messages.append(("system", system_prompt))
        messages.append(("human", prompt))

        async for chunk in self._llm.astream(messages):
            if chunk.content:
                yield chunk.content

    def model_name(self) -> str:
        return self._model


class OllamaEmbeddingProvider(EmbeddingProvider):
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "nomic-embed-text",
    ):
        self._model = model
        self._embeddings = OllamaEmbeddings(
            base_url=base_url,
            model=model,
        )
        self._dimension: int | None = None

    async def embed(self, text: str) -> list[float]:
        return await self._embeddings.aembed_query(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return await self._embeddings.aembed_documents(texts)

    def dimension(self) -> int:
        if self._dimension is None:
            import asyncio

            vec = asyncio.get_event_loop().run_until_complete(self.embed("probe"))
            self._dimension = len(vec)
        return self._dimension

    def model_name(self) -> str:
        return self._model

    @property
    def langchain_embeddings(self) -> OllamaEmbeddings:
        return self._embeddings
