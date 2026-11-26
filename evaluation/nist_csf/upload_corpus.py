import hashlib
import json
import time
from pathlib import Path

import httpx


ROOT = Path(__file__).parent
CORPUS_DIR = ROOT / "corpus"
MANIFEST_PATH = ROOT / "corpus_manifest.json"
API_URL = "http://localhost:8000/api/v1/documents/upload"
DOCUMENTS_URL = "http://localhost:8000/api/v1/documents/"
MAX_INDEX_WAIT_SECONDS = 600
INDEX_POLL_INTERVAL_SECONDS = 5


def indexed_document_ids(client: httpx.Client, collection_name: str) -> set[str]:
    response = client.get(
        DOCUMENTS_URL,
        params={"collection_name": collection_name},
    )
    response.raise_for_status()
    return {
        document["document_id"]
        for document in response.json().get("documents", [])
    }


def wait_until_indexed(
    client: httpx.Client, document_id: str, collection_name: str
) -> bool:
    deadline = time.monotonic() + MAX_INDEX_WAIT_SECONDS
    while time.monotonic() < deadline:
        if document_id in indexed_document_ids(client, collection_name):
            return True
        time.sleep(INDEX_POLL_INTERVAL_SECONDS)
    return False


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    timeout = httpx.Timeout(connect=15, read=600, write=180, pool=15)
    with httpx.Client(timeout=timeout) as client:
        indexed = indexed_document_ids(client, manifest[0]["collection_name"])
        for item in manifest:
            if item["document_id"] in indexed:
                print(f"Already indexed {item['filename']}; skipping.")
                continue

            path = CORPUS_DIR / item["filename"]
            content_hash = hashlib.sha256(path.read_bytes()).hexdigest()
            if content_hash != item["sha256"]:
                raise RuntimeError(f"SHA-256 mismatch for {item['filename']}")
            try:
                with path.open("rb") as file:
                    response = client.post(
                        API_URL,
                        data={"collection_name": item["collection_name"]},
                        files={"file": (item["filename"], file)},
                    )
                response.raise_for_status()
            except httpx.ReadTimeout as error:
                if wait_until_indexed(
                    client, item["document_id"], item["collection_name"]
                ):
                    indexed.add(item["document_id"])
                    print(
                        f"Upload response timed out, but {item['filename']} "
                        "was indexed successfully."
                    )
                    continue
                raise RuntimeError(
                    f"Timed out waiting for {item['filename']} to index. "
                    "The server may still be processing it; rerun this script "
                    "to resume safely."
                ) from error
            except httpx.HTTPStatusError as error:
                if error.response.status_code == 409 and wait_until_indexed(
                    client, item["document_id"], item["collection_name"]
                ):
                    indexed.add(item["document_id"])
                    print(
                        f"{item['filename']} was already processing and is now indexed."
                    )
                    continue
                raise

            result = response.json()
            if result["document_id"] != item["document_id"]:
                raise RuntimeError(
                    f"Document ID mismatch for {item['filename']}: "
                    f"expected {item['document_id']}, got {result['document_id']}"
                )
            indexed.add(item["document_id"])
            print(
                f"Uploaded {item['filename']}: "
                f"{result['chunk_count']} chunks, id={result['document_id']}"
            )
    print(f"Uploaded and verified {len(manifest)} NIST documents.")


if __name__ == "__main__":
    main()
