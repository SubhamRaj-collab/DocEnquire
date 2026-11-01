import json
from pathlib import Path

import httpx


ROOT = Path(__file__).parent
CORPUS_DIR = ROOT / "corpus"
MANIFEST_PATH = ROOT / "corpus_manifest.json"


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    with httpx.Client(timeout=180) as client:
        for item in manifest:
            path = CORPUS_DIR / item["filename"]
            with path.open("rb") as file:
                response = client.post(
                    "http://localhost:8000/api/v1/documents/upload",
                    data={"collection_name": item["collection_name"]},
                    files={"file": (item["filename"], file)},
                )
            response.raise_for_status()
            result = response.json()
            if result["document_id"] != item["document_id"]:
                raise RuntimeError(
                    f"Document ID mismatch for {item['filename']}: "
                    f"expected {item['document_id']}, got {result['document_id']}"
                )
            print(
                f"Uploaded {item['filename']}: "
                f"{result['chunk_count']} chunks, id={result['document_id']}"
            )

    print(f"Uploaded and verified {len(manifest)} corpus files.")


if __name__ == "__main__":
    main()
