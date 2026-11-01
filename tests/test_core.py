import asyncio
from itertools import pairwise

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.privacy import redact_pii
from src.core.config import Settings
from src.rag.citation_parser import CitationParser
from src.rag.context_builder import ContextBuilder
from src.rag.pipeline import RAGPipeline
from src.rag.retriever import ChromaRetriever
from src.schemas.query import QueryRequest


def test_redacts_email_and_phone_numbers() -> None:
    text = "Contact alex@example.com or call 555-123-4567."

    redacted = redact_pii(text)

    assert "alex@example.com" not in redacted
    assert "555-123-4567" not in redacted
    assert "[REDACTED_EMAIL]" in redacted
    assert "[REDACTED_PHONE]" in redacted


def test_chunking_respects_configured_size_and_overlap() -> None:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=12,
        chunk_overlap=3,
        separators=[""],
    )

    chunks = splitter.split_text("abcdefghijklmnopqrstuvwx")

    assert len(chunks) > 1
    assert all(len(chunk) <= 12 for chunk in chunks)
    assert any(left[-3:] == right[:3] for left, right in pairwise(chunks))


def test_query_validation_rejects_empty_question() -> None:
    try:
        QueryRequest(question="")
    except ValueError:
        return
    raise AssertionError("An empty question must fail schema validation")


def test_empty_optional_connection_settings_use_local_mode() -> None:
    settings = Settings(chroma_host="", database_url="")

    assert settings.chroma_host is None
    assert settings.database_url is None


def test_query_redacts_pii_before_retrieval() -> None:
    class FakeRetriever:
        query = ""

        async def retrieve(self, query, **kwargs):
            self.query = query
            return []

    class FakeLLM:
        def model_name(self):
            return "test"

    retriever = FakeRetriever()
    pipeline = RAGPipeline(
        retriever=retriever,
        context_builder=ContextBuilder(),
        llm_provider=FakeLLM(),
        citation_parser=CitationParser(),
        system_prompt="test",
    )

    asyncio.run(pipeline.query("Contact alex@example.com at 555-123-4567"))

    assert "alex@example.com" not in retriever.query
    assert "555-123-4567" not in retriever.query


def test_retriever_maps_chroma_documents() -> None:
    class FakeStore:
        def similarity_search_with_score(self, **kwargs):
            assert kwargs["k"] == 2
            return [
                (
                    Document(
                        page_content="document text",
                        metadata={"document_id": "doc-1", "chunk_index": 3},
                    ),
                    0.25,
                )
            ]

    retriever = ChromaRetriever(FakeStore())

    results = asyncio.run(retriever.retrieve("question", top_k=2))

    assert len(results) == 1
    assert results[0].text == "document text"
    assert results[0].document_id == "doc-1"
    assert results[0].chunk_index == 3
