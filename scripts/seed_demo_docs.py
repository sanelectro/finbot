#!/usr/bin/env python3
"""Seed demo documents through the document CRUD APIs.

This script intentionally uses only HTTP document APIs so both PostgreSQL
metadata and Qdrant embeddings are kept in sync by the backend lifecycle.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib import error, request


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md", ".csv", ".xlsx", ".json"}
COLLECTION_ROLE_MAP: Dict[str, str] = {
    "general": "employee",
    "finance": "finance",
    "engineering": "engineering",
    "marketing": "marketing",
    "hr": "hr",
}
SEED_NAME_PREFIX = "seed::"


def _http_json(method: str, url: str, payload: Dict[str, Any] | None = None) -> Any:
    """Send JSON HTTP request and parse JSON response when available."""
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url=url, method=method, data=data, headers=headers)
    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else None
    except error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} failed ({exc.code}): {err_body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"{method} {url} failed: {exc}") from exc


def _multipart_body(fields: Dict[str, str], file_field: str, file_path: Path) -> Tuple[bytes, str]:
    """Build multipart/form-data body for upload endpoint."""
    boundary = f"----finbot-seed-{uuid.uuid4().hex}"
    chunks: List[bytes] = []

    for key, value in fields.items():
        chunks.append(f"--{boundary}\r\n".encode("utf-8"))
        chunks.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode("utf-8"))
        chunks.append(f"{value}\r\n".encode("utf-8"))

    chunks.append(f"--{boundary}\r\n".encode("utf-8"))
    chunks.append(
        (
            f'Content-Disposition: form-data; name="{file_field}"; '
            f'filename="{file_path.name}"\r\n'
        ).encode("utf-8")
    )
    chunks.append(b"Content-Type: application/octet-stream\r\n\r\n")
    chunks.append(file_path.read_bytes())
    chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(chunks)
    content_type = f"multipart/form-data; boundary={boundary}"
    return body, content_type


def _http_upload(url: str, file_path: Path, collection: str, role_access: str) -> Dict[str, Any]:
    """Upload file using multipart/form-data request."""
    body, content_type = _multipart_body(
        fields={"collection": collection, "role_access": role_access},
        file_field="file",
        file_path=file_path,
    )
    req = request.Request(
        url=url,
        method="POST",
        data=body,
        headers={"Content-Type": content_type, "Accept": "application/json"},
    )
    try:
        with request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        err_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"POST {url} failed ({exc.code}): {err_body}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"POST {url} failed: {exc}") from exc


def _discover_demo_docs(project_root: Path) -> List[Tuple[str, str, Path, str]]:
    """Find one supported source file per collection.

    Returns list of tuples:
    (collection, role_access, file_path, seeded_display_name)
    """
    docs: List[Tuple[str, str, Path, str]] = []

    for collection, role_access in COLLECTION_ROLE_MAP.items():
        collection_dir = project_root / "data" / collection
        if not collection_dir.exists():
            logger.warning("Collection folder missing, skipping: %s", collection_dir)
            continue

        candidates = sorted(
            [
                file_path
                for file_path in collection_dir.iterdir()
                if file_path.is_file() and file_path.suffix.lower() in ALLOWED_SUFFIXES
            ]
        )

        if not candidates:
            logger.warning("No supported files found for collection '%s'", collection)
            continue

        file_path = candidates[0]
        seeded_display_name = f"{SEED_NAME_PREFIX}{collection}::{file_path.name}"
        docs.append((collection, role_access, file_path, seeded_display_name))

    return docs


def _wait_until_processed(base_url: str, document_id: int, timeout_seconds: int = 300) -> Dict[str, Any]:
    """Poll document until upload and embedding statuses are completed."""
    start = time.time()

    while time.time() - start < timeout_seconds:
        document = _http_json("GET", f"{base_url}/documents/{document_id}")
        upload_status = str(document.get("upload_status", ""))
        embedding_status = str(document.get("embedding_status", ""))

        if upload_status == "completed" and embedding_status == "completed":
            return document

        if upload_status == "failed" or embedding_status == "failed":
            message = document.get("error_message") or "Unknown processing failure"
            raise RuntimeError(
                f"Document {document_id} failed processing: {message}"
            )

        time.sleep(2)

    raise RuntimeError(f"Timed out waiting for document {document_id} to finish processing")


def seed_demo_docs() -> int:
    """Seed demo documents using CRUD APIs to keep Postgres and Qdrant in sync."""
    api_base_url = os.getenv("FINBOT_API_BASE_URL", "http://localhost:8000/api/v1").rstrip("/")
    project_root = Path(__file__).resolve().parent.parent

    logger.info("🌱 Starting demo document seeding using API: %s", api_base_url)

    # Basic API readiness check
    _http_json("GET", f"{api_base_url}/documents?page=1&page_size=1")

    demo_docs = _discover_demo_docs(project_root)
    if not demo_docs:
        logger.error("❌ No supported demo documents found under data/*")
        return 1

    logger.info("Found %d demo document(s) to seed", len(demo_docs))

    # Delete previously seeded docs so operation is idempotent.
    existing = _http_json("GET", f"{api_base_url}/documents?page=1&page_size=100")
    existing_docs = existing.get("documents", []) if isinstance(existing, dict) else []
    prior_seeded = [doc for doc in existing_docs if str(doc.get("original_filename", "")).startswith(SEED_NAME_PREFIX)]

    deleted_count = 0
    for doc in prior_seeded:
        doc_id = int(doc["id"])
        _http_json("DELETE", f"{api_base_url}/documents/{doc_id}")
        deleted_count += 1
        logger.info("🧹 Deleted previous seeded document id=%s", doc_id)

    if deleted_count:
        logger.info("Removed %d previous seeded document(s)", deleted_count)

    created_count = 0
    updated_count = 0

    for collection, role_access, file_path, seeded_name in demo_docs:
        logger.info("⬆️ Uploading %s -> collection=%s, role=%s", file_path.name, collection, role_access)
        upload_response = _http_upload(
            f"{api_base_url}/documents/upload",
            file_path=file_path,
            collection=collection,
            role_access=role_access,
        )

        document_id = int(upload_response["document_id"])
        created_count += 1

        _wait_until_processed(api_base_url, document_id)

        # Use update endpoint so seeded records are clearly identifiable.
        _http_json(
            "PUT",
            f"{api_base_url}/documents/{document_id}",
            payload={"original_filename": seeded_name},
        )
        updated_count += 1

        seeded_doc = _http_json("GET", f"{api_base_url}/documents/{document_id}")
        if seeded_doc.get("collection") != collection or seeded_doc.get("role_access") != role_access:
            raise RuntimeError(
                f"Document {document_id} metadata mismatch after seed. "
                f"Expected collection={collection}, role_access={role_access}, "
                f"got collection={seeded_doc.get('collection')}, role_access={seeded_doc.get('role_access')}"
            )

        logger.info("✅ Seeded doc id=%s (%s)", document_id, seeded_name)

    logger.info("🎉 Demo document seeding completed")
    logger.info("📊 Summary: created=%d updated=%d", created_count, updated_count)
    return 0


def main() -> int:
    try:
        return seed_demo_docs()
    except Exception as exc:
        logger.error("❌ Demo document seeding failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
