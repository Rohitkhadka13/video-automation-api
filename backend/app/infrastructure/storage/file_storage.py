# =============================================================================
# app/infrastructure/storage/file_storage.py
# Pluggable file storage abstraction — local filesystem or S3-compatible.
# Toggle via STORAGE_BACKEND=local|s3 in .env.
# Both backends expose the same async interface.
# =============================================================================
from __future__ import annotations

import asyncio
import hashlib
import os
import shutil
import tempfile
from pathlib import Path
from typing import BinaryIO
from uuid import uuid4

import aiofiles
import aiofiles.os

from app.core.config import settings
from app.core.exceptions import FileNotFoundInStorageError, StorageError
from app.core.logging import get_logger

logger = get_logger(__name__)


class FileStorage:
    """
    Unified file storage interface.

    Methods are the same regardless of backend (local vs S3).
    The backend is chosen at construction time from settings.STORAGE_BACKEND.
    """

    def __init__(self) -> None:
        self._backend = settings.STORAGE_BACKEND
        if self._backend == "s3":
            self._s3 = _S3Backend()
        else:
            self._local = _LocalBackend()

    async def upload(
        self,
        file_obj: BinaryIO,
        *,
        key: str | None = None,
        prefix: str = "uploads",
        original_filename: str = "",
        content_type: str = "application/octet-stream",
    ) -> str:
        """
        Upload a file-like object to storage.

        Args:
            file_obj:          Seekable binary file-like object.
            key:               Explicit storage key. Auto-generated if None.
            prefix:            Directory prefix (e.g. "uploads", "processed").
            original_filename: Original filename for extension extraction.
            content_type:      MIME type for S3 metadata.

        Returns:
            Storage key (relative path or S3 object key).
        """
        if key is None:
            ext = Path(original_filename).suffix if original_filename else ""
            key = f"{prefix}/{uuid4().hex}{ext}"

        if self._backend == "s3":
            return await self._s3.upload(file_obj, key=key, content_type=content_type)
        return await self._local.upload(file_obj, key=key)

    async def upload_from_path(
        self,
        local_path: str | Path,
        *,
        prefix: str = "processed",
        key: str | None = None,
    ) -> str:
        """
        Upload a local file to storage.

        Args:
            local_path: Path to the local file.
            prefix:     Storage directory prefix.
            key:        Explicit storage key. Auto-generated if None.

        Returns:
            Storage key.
        """
        path = Path(local_path)
        if not path.exists():
            raise StorageError(f"Local file not found: {local_path}")

        if key is None:
            key = f"{prefix}/{uuid4().hex}{path.suffix}"

        async with aiofiles.open(path, "rb") as f:
            content = await f.read()

        if self._backend == "s3":
            return await self._s3.upload_bytes(content, key=key)
        return await self._local.upload_bytes(content, key=key)

    async def download(self, key: str) -> bytes:
        """
        Download a stored file as bytes.

        Raises:
            FileNotFoundInStorageError: If the key does not exist.
        """
        if self._backend == "s3":
            return await self._s3.download(key)
        return await self._local.download(key)

    async def download_to_temp(self, key: str) -> str:
        """
        Download a stored file to a temporary local path.

        Returns:
            Absolute path to the temp file (caller must delete when done).

        Raises:
            FileNotFoundInStorageError: If the key does not exist.
        """
        data = await self.download(key)
        ext = Path(key).suffix
        tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
        tmp.write(data)
        tmp.flush()
        tmp.close()
        return tmp.name

    async def delete(self, key: str) -> bool:
        """
        Delete a stored file.

        Returns:
            True if deleted, False if key did not exist.
        """
        if self._backend == "s3":
            return await self._s3.delete(key)
        return await self._local.delete(key)

    async def exists(self, key: str) -> bool:
        """Return True if the storage key exists."""
        if self._backend == "s3":
            return await self._s3.exists(key)
        return await self._local.exists(key)

    def public_url(self, key: str) -> str:
        """Return the public-facing URL for a storage key."""
        if self._backend == "s3":
            return self._s3.public_url(key)
        return self._local.public_url(key)

    async def presigned_url(self, key: str, expires: int | None = None) -> str:
        """
        Return a pre-signed URL for direct download (S3 only).
        For local backend, falls back to public_url().
        """
        if self._backend == "s3":
            return await self._s3.presigned_url(
                key, expires=expires or settings.S3_PRESIGNED_URL_EXPIRY
            )
        return self._local.public_url(key)


# ---------------------------------------------------------------------------
# Local filesystem backend
# ---------------------------------------------------------------------------

class _LocalBackend:
    def __init__(self) -> None:
        self._root = Path(settings.MEDIA_ROOT)
        self._root.mkdir(parents=True, exist_ok=True)

    def _abs_path(self, key: str) -> Path:
        # Strip leading slashes to prevent path traversal
        safe_key = key.lstrip("/")
        return self._root / safe_key

    async def upload(self, file_obj: BinaryIO, *, key: str) -> str:
        return await self.upload_bytes(file_obj.read(), key=key)

    async def upload_bytes(self, data: bytes, *, key: str) -> str:
        path = self._abs_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(path, "wb") as f:
            await f.write(data)
        logger.debug("storage.local.upload", key=key, size=len(data))
        return key

    async def download(self, key: str) -> bytes:
        path = self._abs_path(key)
        if not path.exists():
            raise FileNotFoundInStorageError(f"File not found in local storage: {key}")
        async with aiofiles.open(path, "rb") as f:
            return await f.read()

    async def delete(self, key: str) -> bool:
        path = self._abs_path(key)
        if not path.exists():
            return False
        await aiofiles.os.remove(path)
        return True

    async def exists(self, key: str) -> bool:
        return self._abs_path(key).exists()

    def public_url(self, key: str) -> str:
        return f"{settings.MEDIA_URL}{key.lstrip('/')}"


# ---------------------------------------------------------------------------
# S3-compatible backend (AWS S3 / MinIO / Backblaze B2 / R2)
# ---------------------------------------------------------------------------

class _S3Backend:
    def __init__(self) -> None:
        try:
            import aiobotocore.session  # type: ignore[import]
            self._session = aiobotocore.session.get_session()
        except ImportError as exc:
            raise StorageError(
                "S3 storage requires aiobotocore. "
                "Add it to requirements.txt: aiobotocore[boto3]"
            ) from exc

        self._bucket = settings.S3_BUCKET_NAME
        self._region = settings.S3_REGION
        self._endpoint = settings.S3_ENDPOINT_URL or None

    def _client_context(self):  # noqa: ANN201
        return self._session.create_client(
            "s3",
            region_name=self._region,
            endpoint_url=self._endpoint,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY,
        )

    async def upload(
        self, file_obj: BinaryIO, *, key: str, content_type: str = "application/octet-stream"
    ) -> str:
        return await self.upload_bytes(file_obj.read(), key=key, content_type=content_type)

    async def upload_bytes(
        self,
        data: bytes,
        *,
        key: str,
        content_type: str = "application/octet-stream",
    ) -> str:
        async with self._client_context() as s3:
            await s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        logger.debug("storage.s3.upload", key=key, size=len(data))
        return key

    async def download(self, key: str) -> bytes:
        async with self._client_context() as s3:
            try:
                response = await s3.get_object(Bucket=self._bucket, Key=key)
                return await response["Body"].read()
            except s3.exceptions.NoSuchKey:
                raise FileNotFoundInStorageError(f"Key not found in S3: {key}")

    async def delete(self, key: str) -> bool:
        async with self._client_context() as s3:
            await s3.delete_object(Bucket=self._bucket, Key=key)
        return True

    async def exists(self, key: str) -> bool:
        async with self._client_context() as s3:
            try:
                await s3.head_object(Bucket=self._bucket, Key=key)
                return True
            except Exception:
                return False

    def public_url(self, key: str) -> str:
        if self._endpoint:
            return f"{self._endpoint}/{self._bucket}/{key}"
        return f"https://{self._bucket}.s3.{self._region}.amazonaws.com/{key}"

    async def presigned_url(self, key: str, expires: int = 3600) -> str:
        async with self._client_context() as s3:
            url = await s3.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires,
            )
        return url