import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.exceptions import IngestionError
from src.ingestion.parsers.registry import ParserRegistry
from src.storage.file_store import FileStore
from src.vectorstore.chroma_store import ChromaStore

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    document_id: str
    filename: str
    doc_type: str
    chunk_count: int
    collection_name: str
    file_size_bytes: int
    upload_timestamp: str


class IngestionPipeline:
    def __init__(
        self,
        parser_registry: ParserRegistry,
        vector_store: ChromaStore,
        file_store: FileStore,
        chunk_size: int = 2048,
        chunk_overlap: int = 256,
    ) -> None:
        self.parser_registry = parser_registry
        self.vector_store = vector_store
        self.file_store = file_store
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    async def ingest(
        self,
        file_path: str,
        filename: str,
        collection_name: str = "default",
    ) -> IngestionResult:
        document_id = str(uuid4())
        doc_type = Path(filename).suffix.lstrip(".").lower()
        file_size = Path(file_path).stat().st_size
        upload_ts = datetime.now(timezone.utc).isoformat()

        try:
            stored_path = self.file_store.store(file_path, document_id, filename)

            parser = self.parser_registry.get_parser(filename)
            segments = parser.parse(stored_path)

            if not segments:
                raise IngestionError(f"No content extracted from '{filename}'")

            lc_docs = []
            for seg in segments:
                metadata = {
                    "document_id": document_id,
                    "filename": filename,
                    "doc_type": doc_type,
                    "upload_timestamp": upload_ts,
                }
                if seg.page_number is not None:
                    metadata["page_number"] = seg.page_number
                if seg.section_title:
                    metadata["section_title"] = seg.section_title
                if seg.slide_number is not None:
                    metadata["slide_number"] = seg.slide_number
                if seg.sheet_name:
                    metadata["sheet_name"] = seg.sheet_name

                lc_docs.append(Document(page_content=seg.text, metadata=metadata))

            chunks = self._splitter.split_documents(lc_docs)

            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"] = i
                chunk.metadata["chunk_count"] = len(chunks)

            ids = [f"{document_id}_{i}" for i in range(len(chunks))]

            self.vector_store.add_documents(
                documents=chunks,
                ids=ids,
                collection_name=collection_name,
            )

            logger.info(
                "Ingested '%s' -> %d chunks into collection '%s'",
                filename,
                len(chunks),
                collection_name,
            )

            return IngestionResult(
                document_id=document_id,
                filename=filename,
                doc_type=doc_type,
                chunk_count=len(chunks),
                collection_name=collection_name,
                file_size_bytes=file_size,
                upload_timestamp=upload_ts,
            )

        except IngestionError:
            raise
        except Exception as e:
            self.file_store.delete(document_id)
            raise IngestionError(f"Failed to ingest '{filename}': {e}") from e
