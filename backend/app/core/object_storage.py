"""S3-compatible object storage — MinIO in dev, a drop-in AWS S3 endpoint in
production (same client code, only endpoint/credentials change; see
docs/tech-stack.md's ObjectStorage entry). boto3 is synchronous; every call
here runs it via asyncio.to_thread so callers stay async without pulling in
a separate boto3-async dependency.
"""

import asyncio

import boto3
from botocore.client import Config as BotoConfig
from botocore.exceptions import ClientError

from app.core.config import Settings


class ObjectStorage:
    def __init__(self, settings: Settings) -> None:
        scheme = "https" if settings.minio_use_ssl else "http"
        self._client = boto3.client(
            "s3",
            endpoint_url=f"{scheme}://{settings.minio_endpoint}",
            aws_access_key_id=settings.minio_root_user,
            aws_secret_access_key=settings.minio_root_password,
            config=BotoConfig(signature_version="s3v4"),
        )
        self._documents_bucket = settings.minio_bucket_documents
        # Bucket existence is checked once per process, not once per call —
        # cheap idempotent setup, not a per-upload/download round trip.
        self._bucket_ready = False

    def _ensure_bucket_sync(self) -> None:
        if self._bucket_ready:
            return
        try:
            self._client.head_bucket(Bucket=self._documents_bucket)
        except ClientError:
            self._client.create_bucket(Bucket=self._documents_bucket)
        self._bucket_ready = True

    async def upload(self, key: str, content: bytes, *, content_type: str | None = None) -> None:
        def _put() -> None:
            self._ensure_bucket_sync()
            extra = {"ContentType": content_type} if content_type else {}
            self._client.put_object(Bucket=self._documents_bucket, Key=key, Body=content, **extra)

        await asyncio.to_thread(_put)

    async def download(self, key: str) -> bytes:
        def _get() -> bytes:
            self._ensure_bucket_sync()
            response = self._client.get_object(Bucket=self._documents_bucket, Key=key)
            body: bytes = response["Body"].read()
            return body

        return await asyncio.to_thread(_get)
