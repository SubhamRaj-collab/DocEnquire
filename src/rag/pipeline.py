import json
import time
from collections.abc import AsyncIterator
from dataclasses import asdict

from src.llm.base import LLMProvider
from src.rag.citation_parser import CitationParser
from src.rag.context_builder import ContextBuilder
from src.rag.retriever import ChromaRetriever
from src.core.metrics import time_to_first_token
from src.core.privacy import redact_pii

class RAGPipeline:
    def __init__(
        self,
        retriever: ChromaRetriever,
        context_builder: ContextBuilder,
        llm_provider: LLMProvider,
        citation_parser: CitationParser,
        system_prompt: str,
        redact_personal_data: bool = True,
    ) -> None:
        self.retriever = retriever
        self.context_builder = context_builder
        self.llm = llm_provider
        self.citation_parser = citation_parser
        self.system_prompt = system_prompt
        self.redact_personal_data = redact_personal_data

    async def query(
        self,
        question: str,
        collection_name: str = "default",
        top_k: int = 5,
        temperature: float = 0.1,
        metadata_filter: dict | None = None,
    ) -> dict:
        if self.redact_personal_data:
            question = redact_pii(question)
        chunks = await self.retriever.retrieve(
            query=question,
            collection_name=collection_name,
            top_k=top_k,
            where_filter=metadata_filter,
        )

        if not chunks:
            return {
                "answer": "No relevant documents found for your question.",
                "citations": [],
                "source_documents": [],
                "model": self.llm.model_name(),
                "usage": None,
            }

        context_text, source_map = self.context_builder.build(chunks)

        user_prompt = (
            f"CONTEXT:\n{context_text}\n\n"
            f"QUESTION: {question}\n\n"
            f"Provide your answer with source citations as instructed."
        )

        llm_response = await self.llm.generate(
            prompt=user_prompt,
            system_prompt=self.system_prompt,
            temperature=temperature,
        )

        answer, citations = self.citation_parser.parse(llm_response.text, source_map)

        return {
            "answer": answer,
            "citations": [asdict(c) for c in citations],
            "source_documents": [
                {
                    "document_id": s["document_id"],
                    "filename": s.get("filename"),
                    "chunk_text": s.get("chunk_text"),
                    "page_number": s.get("page_number"),
                    "section_title": s.get("section_title"),
                    "slide_number": s.get("slide_number"),
                    "sheet_name": s.get("sheet_name"),
                    "relevance_score": s.get("relevance_score"),
                }
                for s in source_map
            ],
            "model": llm_response.model,
            "usage": llm_response.usage,
        }

    async def query_stream(
        self,
        question: str,
        collection_name: str = "default",
        top_k: int = 5,
        temperature: float = 0.1,
    ) -> AsyncIterator[str]:
        started = time.perf_counter()
        if self.redact_personal_data:
            question = redact_pii(question)
        chunks = await self.retriever.retrieve(
            query=question,
            collection_name=collection_name,
            top_k=top_k,
        )

        if not chunks:
            yield json.dumps(
                {"type": "token", "data": "No relevant documents found for your question."}
            )
            yield json.dumps({"type": "done", "data": None})
            return

        context_text, source_map = self.context_builder.build(chunks)

        user_prompt = (
            f"CONTEXT:\n{context_text}\n\n"
            f"QUESTION: {question}\n\n"
            f"Provide your answer with source citations as instructed."
        )
        accumulated = ""
        observed_first_token = False
        async for token in self.llm.stream(
            prompt=user_prompt,
            system_prompt=self.system_prompt,
            temperature=temperature,
        ):
            if not observed_first_token:
                time_to_first_token.observe(time.perf_counter() - started)
                observed_first_token = True
            accumulated += token
            yield json.dumps({"type": "token", "data": token})

        answer, citations = self.citation_parser.parse(accumulated, source_map)

        yield json.dumps({
            "type": "citations",
            "data": [asdict(c) for c in citations],
        })

        yield json.dumps({"type": "done", "data": None})
