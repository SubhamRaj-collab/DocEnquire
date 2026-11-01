from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

import psycopg

from src.core.exceptions import IngestionInProgressError


@dataclass(frozen=True)
class ExistingIngestion:
    document_id: str
    chunk_count: int
    file_size_bytes: int
    upload_timestamp: str


class PostgresJobStore:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def ensure_schema(self) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS ingestion_jobs (
                    id BIGSERIAL PRIMARY KEY,
                    content_sha256 TEXT NOT NULL,
                    collection_name TEXT NOT NULL,
                    document_id TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN
                        ('queued', 'processing', 'indexed', 'failed')),
                    chunk_count INTEGER NOT NULL DEFAULT 0,
                    file_size_bytes BIGINT NOT NULL DEFAULT 0,
                    upload_timestamp TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    error TEXT,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (content_sha256, collection_name)
                )
                """
            )

    def begin(
        self,
        content_sha256: str,
        collection_name: str,
        document_id: str,
        filename: str,
        doc_type: str,
        file_size_bytes: int,
        upload_timestamp: str,
    ) -> ExistingIngestion | None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                INSERT INTO ingestion_jobs
                    (content_sha256, collection_name, document_id, filename, doc_type,
                     status, file_size_bytes, upload_timestamp)
                VALUES (%s, %s, %s, %s, %s, 'queued', %s, %s)
                ON CONFLICT (content_sha256, collection_name) DO NOTHING
                """,
                (
                    content_sha256,
                    collection_name,
                    document_id,
                    filename,
                    doc_type,
                    file_size_bytes,
                    upload_timestamp,
                ),
            )

        with psycopg.connect(self.database_url) as connection:
            row = connection.execute(
                """
                SELECT document_id, status, chunk_count, file_size_bytes, upload_timestamp,
                    updated_at > NOW() - INTERVAL '30 minutes'
                FROM ingestion_jobs
                WHERE content_sha256 = %s AND collection_name = %s
                FOR UPDATE
                """,
                (content_sha256, collection_name),
            ).fetchone()
            if row[1] == "indexed":
                return ExistingIngestion(row[0], row[2], row[3], row[4])
            if row[1] == "processing" and row[5]:
                raise IngestionInProgressError(
                    "An ingestion job for this content is already processing"
                )
            connection.execute(
                """
                UPDATE ingestion_jobs
                SET status = 'processing', attempts = attempts + 1, error = NULL,
                    filename = %s, doc_type = %s, updated_at = NOW()
                WHERE content_sha256 = %s AND collection_name = %s
                """,
                (filename, doc_type, content_sha256, collection_name),
            )
        return None

    def finish(
        self, content_sha256: str, collection_name: str, chunk_count: int
    ) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                UPDATE ingestion_jobs
                SET status = 'indexed', chunk_count = %s, error = NULL, updated_at = NOW()
                WHERE content_sha256 = %s AND collection_name = %s
                """,
                (chunk_count, content_sha256, collection_name),
            )

    def fail(self, content_sha256: str, collection_name: str, error: str) -> None:
        with psycopg.connect(self.database_url) as connection:
            connection.execute(
                """
                UPDATE ingestion_jobs
                SET status = 'failed', error = %s, updated_at = NOW()
                WHERE content_sha256 = %s AND collection_name = %s
                """,
                (error[:2000], content_sha256, collection_name),
            )


def deterministic_document_id(content_sha256: str, collection_name: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"docenquire:{collection_name}:{content_sha256}"))


def utc_timestamp() -> str:
    return datetime.now(UTC).isoformat()
