"""
Object Storage module for presentations.
Handles uploading/downloading PDFs from Emergent Object Storage.
"""

import os
import requests
import logging

logger = logging.getLogger(__name__)

STORAGE_URL = "https://integrations.emergentagent.com/objstore/api/v1/storage"
APP_NAME = "proyecto-residente"

_storage_key = None


def _get_emergent_key():
    return os.environ.get("EMERGENT_LLM_KEY", "")


def init_storage():
    """Initialize storage session. Call once at startup."""
    global _storage_key
    if _storage_key:
        return _storage_key
    key = _get_emergent_key()
    if not key:
        logger.warning("EMERGENT_LLM_KEY not set, object storage disabled")
        return None
    try:
        resp = requests.post(
            f"{STORAGE_URL}/init",
            json={"emergent_key": key},
            timeout=30,
        )
        resp.raise_for_status()
        _storage_key = resp.json()["storage_key"]
        logger.info("Object storage initialized")
        return _storage_key
    except Exception as e:
        logger.error(f"Object storage init failed: {e}")
        return None


def _ensure_key():
    global _storage_key
    if not _storage_key:
        init_storage()
    return _storage_key


def put_pdf(presentation_id: str, data: bytes) -> dict:
    """Upload a PDF to object storage. Returns result dict or None on failure."""
    key = _ensure_key()
    if not key:
        return None
    path = f"{APP_NAME}/presentations/{presentation_id}.pdf"
    try:
        resp = requests.put(
            f"{STORAGE_URL}/objects/{path}",
            headers={"X-Storage-Key": key, "Content-Type": "application/pdf"},
            data=data,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Upload failed for {presentation_id}: {e}")
        return None


def get_pdf(storage_path: str) -> bytes:
    """Download a PDF from object storage. Returns bytes or None."""
    key = _ensure_key()
    if not key:
        return None
    try:
        resp = requests.get(
            f"{STORAGE_URL}/objects/{storage_path}",
            headers={"X-Storage-Key": key},
            timeout=60,
        )
        resp.raise_for_status()
        return resp.content
    except Exception as e:
        logger.error(f"Download failed for {storage_path}: {e}")
        return None
