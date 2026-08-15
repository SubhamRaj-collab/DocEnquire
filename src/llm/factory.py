from src.core.config import Settings
from src.llm.base import EmbeddingProvider, LLMProvider


class ProviderFactory:
    @staticmethod
    def create_llm(settings: Settings) -> LLMProvider:
        match settings.llm_provider:
            case "ollama":
                from src.llm.providers.ollama import OllamaLLMProvider

                return OllamaLLMProvider(
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_llm_model,
                )
            case "claude":
                from src.llm.providers.claude import ClaudeLLMProvider

                return ClaudeLLMProvider(
                    model=settings.claude_model,
                    api_key=settings.claude_api_key,
                )
            case "openai":
                from src.llm.providers.openai_provider import OpenAILLMProvider

                return OpenAILLMProvider(
                    model=settings.openai_model,
                    api_key=settings.openai_api_key,
                    azure_endpoint=settings.azure_openai_endpoint,
                )
            case _:
                raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")

    @staticmethod
    def create_embedder(settings: Settings) -> EmbeddingProvider:
        match settings.embedding_provider:
            case "ollama":
                from src.llm.providers.ollama import OllamaEmbeddingProvider

                return OllamaEmbeddingProvider(
                    base_url=settings.ollama_base_url,
                    model=settings.ollama_embedding_model,
                )
            case _:
                raise ValueError(f"Unknown embedding provider: {settings.embedding_provider}")
