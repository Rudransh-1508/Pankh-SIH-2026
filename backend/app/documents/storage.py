"""Object storage for encrypted Uploaded Documents, behind one small interface."""

import asyncio
import os
import tempfile
from functools import cache
from pathlib import Path
from typing import Any, Protocol

from app.config import Settings


class ObjectNotFound(Exception):
    pass


class ObjectStore(Protocol):
    async def put(self, key: str, data: bytes) -> None: ...

    async def get(self, key: str) -> bytes: ...

    async def delete(self, key: str) -> None: ...


class FileStore:
    """A local directory. Files are written atomically and readable only by their owner."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root.resolve()):
            raise ValueError(f"Invalid object key: {key}")
        return path

    async def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        handle, temporary = tempfile.mkstemp(dir=path.parent)
        try:
            with os.fdopen(handle, "wb") as file:
                file.write(data)
            os.chmod(temporary, 0o600)
            os.replace(temporary, path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise

    async def get(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except FileNotFoundError as error:
            raise ObjectNotFound(key) from error

    async def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3Store:
    """Any S3-compatible store: Amazon S3 in production, SeaweedFS locally."""

    def __init__(self, client: Any, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    async def put(self, key: str, data: bytes) -> None:
        try:
            await asyncio.to_thread(self._put, key, data)
        except self.client.exceptions.NoSuchBucket:
            # Only in development: production buckets are created, with their policies, by infra.
            await asyncio.to_thread(self._create_bucket)
            await asyncio.to_thread(self._put, key, data)

    def _put(self, key: str, data: bytes) -> None:
        self.client.put_object(
            Bucket=self.bucket, Key=key, Body=data, ContentType="application/octet-stream"
        )

    def _create_bucket(self) -> None:
        region = self.client.meta.region_name
        options = {} if region == "us-east-1" else {"LocationConstraint": region}
        self.client.create_bucket(Bucket=self.bucket, CreateBucketConfiguration=options)

    async def get(self, key: str) -> bytes:
        try:
            response = await asyncio.to_thread(self.client.get_object, Bucket=self.bucket, Key=key)
        except self.client.exceptions.NoSuchKey as error:
            raise ObjectNotFound(key) from error
        return await asyncio.to_thread(response["Body"].read)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=key)


@cache
def _store(
    kind: str,
    path: str,
    bucket: str,
    endpoint_url: str | None,
    region: str,
    access_key_id: str | None,
    secret_access_key: str | None,
) -> ObjectStore:
    if kind == "file":
        return FileStore(path)
    import boto3

    client = boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        region_name=region,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
    )
    return S3Store(client, bucket)


def object_store(settings: Settings) -> ObjectStore:
    return _store(
        settings.object_store,
        settings.object_store_path,
        settings.s3_bucket,
        settings.s3_endpoint_url,
        settings.s3_region,
        settings.s3_access_key_id,
        settings.s3_secret_access_key,
    )
