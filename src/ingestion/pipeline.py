import asyncio
import logging
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.core.exceptions import IngestionError, IngestionInProgressError
from src.core.job_store import (
    PostgresJobStore,
    deterministic_document_id,
    utc_timestamp,
)
from src.core.metrics import ingestion_failures
from src.core.privacy import redact_pii
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
        job_store: PostgresJobStore | None = None,
        redact_personal_data: bool = True,
    ) -> None:
        self.parser_registry = parser_registry
        self.vector_store = vector_store
        self.file_store = file_store
        self.job_store = job_store
        self.redact_personal_data = redact_personal_data
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
        doc_type = Path(filename).suffix.lstrip(".").lower()
        file_size = Path(file_path).stat().st_size
        content_sha256 = sha256(Path(file_path).read_bytes()).hexdigest()
        document_id = deterministic_document_id(content_sha256, collection_name)
        upload_ts = utc_timestamp()

        try:
            if self.job_store:
                existing = self.job_store.begin(
                    content_sha256,
                    collection_name,
                    document_id,
                    filename,
                    doc_type,
                    file_size,
                    upload_ts,
                )
                if existing:
                    return IngestionResult(
                        document_id=existing.document_id,
                        filename=filename,
                        doc_type=doc_type,
                        chunk_count=existing.chunk_count,
                        collection_name=collection_name,
                        file_size_bytes=existing.file_size_bytes,
                        upload_timestamp=existing.upload_timestamp,
                    )

            stored_path = self.file_store.store(file_path, document_id, filename)

            parser = self.parser_registry.get_parser(filename)
            segments = parser.parse(stored_path)

            if not segments:
                raise IngestionError(f"No content extracted from '{filename}'")

            lc_docs = []
            for seg in segments:
                metadata = {
                    "document_id": document_id,
                    "filename": redact_pii(filename) if self.redact_personal_data else filename,
                    "doc_type": doc_type,
                    "upload_timestamp": upload_ts,
                }
                if seg.page_number is not None:
                    metadata["page_number"] = seg.page_number
                if seg.section_title:
                    metadata["section_title"] = (
                        redact_pii(seg.section_title)
                        if self.redact_personal_data
                        else seg.section_title
                    )
                if seg.slide_number is not None:
                    metadata["slide_number"] = seg.slide_number
                if seg.sheet_name:
                    metadata["sheet_name"] = (
                        redact_pii(seg.sheet_name)
                        if self.redact_personal_data
                        else seg.sheet_name
                    )

                content = redact_pii(seg.text) if self.redact_personal_data else seg.text
                lc_docs.append(Document(page_content=content, metadata=metadata))

            chunks = self._splitter.split_documents(lc_docs)

            for i, chunk in enumerate(chunks):
                chunk.metadata["chunk_index"] = i
                chunk.metadata["chunk_count"] = len(chunks)

            ids = [f"{document_id}_{i}" for i in range(len(chunks))]

            for attempt in range(3):
                try:
                    self.vector_store.add_documents(
                        documents=chunks,
                        ids=ids,
                        collection_name=collection_name,
                    )
                    break
                except Exception:
                    if attempt == 2:
                        raise
                    await asyncio.sleep(0.25 * (2**attempt))

            if self.job_store:
                self.job_store.finish(content_sha256, collection_name, len(chunks))

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

        except IngestionInProgressError:
            raise
        except IngestionError as e:
            ingestion_failures.inc()
            if self.job_store:
                self.job_store.fail(content_sha256, collection_name, str(e))
            raise
        except Exception as e:
            self.file_store.delete(document_id)
            ingestion_failures.inc()
            if self.job_store:
                self.job_store.fail(content_sha256, collection_name, str(e))
            raise IngestionError(f"Failed to ingest '{filename}': {e}") from e
