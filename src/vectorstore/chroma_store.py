import logging

from langchain_chroma import Chroma
from langchain_core.documents import Document

from src.core.exceptions import VectorStoreError

logger = logging.getLogger(__name__)


class ChromaStore:
    def __init__(
        self,
        persist_directory: str,
        embedding_function,
        host: str | None = None,
        port: int = 8000,
    ) -> None:
        self._persist_dir = persist_directory
        self._embedding_function = embedding_function
        self._client = None
        if host:
            import chromadb

            self._client = chromadb.HttpClient(host=host, port=port)
        self._collections: dict[str, Chroma] = {}

    def _get_collection(self, name: str) -> Chroma:
        if name not in self._collections:
            self._collections[name] = Chroma(
                collection_name=name,
                persist_directory=self._persist_dir,
                embedding_function=self._embedding_function,
                collection_metadata={"hnsw:space": "cosine"},
                client=self._client,
            )
        return self._collections[name]

    def add_documents(
        self,
        documents: list[Document],
        ids: list[str],
        collection_name: str = "default",
    ) -> None:
        store = self._get_collection(collection_name)
        store.add_documents(documents, ids=ids)
        logger.info("Added %d documents to collection '%s'", len(documents), collection_name)

    def similarity_search_with_score(
        self,
        query: str,
        k: int = 5,
        collection_name: str = "default",
        filter: dict | None = None,
    ) -> list[tuple[Document, float]]:
        store = self._get_collection(collection_name)
        return store.similarity_search_with_score(query, k=k, filter=filter)

    def delete_by_document_id(self, document_id: str, collection_name: str = "default") -> int:
        store = self._get_collection(collection_name)
        try:
            results = store.get(where={"document_id": document_id})
            if results and results["ids"]:
                store.delete(ids=results["ids"])
                return len(results["ids"])
        except Exception as e:
            raise VectorStoreError(f"Failed to delete document {document_id}: {e}") from e
        return 0

    def list_documents(self, collection_name: str = "default") -> list[dict]:
        store = self._get_collection(collection_name)
        try:
            results = store.get(include=["metadatas"])
        except Exception:
            return []

        if not results or not results.get("metadatas"):
            return []

        docs: dict[str, dict] = {}
        for meta in results["metadatas"]:
            if not meta:
                continue
            doc_id = meta.get("document_id", "")
            if doc_id and doc_id not in docs:
                docs[doc_id] = {
                    "document_id": doc_id,
                    "filename": meta.get("filename", ""),
                    "doc_type": meta.get("doc_type", ""),
                    "chunk_count": meta.get("chunk_count", 0),
                    "upload_timestamp": meta.get("upload_timestamp", ""),
                    "collection_name": collection_name,
                }
        return list(docs.values())

    def collection_count(self, name: str = "default") -> int:
        store = self._get_collection(name)
        return store._collection.count()

    def list_collections(self) -> list[str]:
        import chromadb

        client = self._client or chromadb.PersistentClient(path=self._persist_dir)
        return [c.name for c in client.list_collections()]
