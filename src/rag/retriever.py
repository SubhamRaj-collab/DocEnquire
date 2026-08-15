from dataclasses import dataclass

from src.vectorstore.chroma_store import ChromaStore


@dataclass
class RetrievedChunk:
    text: str
    score: float
    metadata: dict
    document_id: str
    chunk_index: int


class ChromaRetriever:
    def __init__(self, chroma_store: ChromaStore) -> None:
        self.store = chroma_store

    async def retrieve(
        self,
        query: str,
        collection_name: str = "default",
        top_k: int = 5,
        score_threshold: float | None = None,
        where_filter: dict | None = None,
    ) -> list[RetrievedChunk]:
        results = self.store.similarity_search_with_score(
            query=query,
            k=top_k,
            collection_name=collection_name,
            filter=where_filter,
        )

        chunks = []
        for doc, score in results:
            if score_threshold is not None and score > score_threshold:
                continue
            chunks.append(
                RetrievedChunk(
                    text=doc.page_content,
                    score=score,
                    metadata=doc.metadata,
                    document_id=doc.metadata.get("document_id", ""),
                    chunk_index=doc.metadata.get("chunk_index", 0),
                )
            )
        return chunks
