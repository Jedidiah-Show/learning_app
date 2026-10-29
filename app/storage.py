"""Small storage abstraction for user files.

Local disk is the development backend. Production uses an S3-compatible
bucket (Cloudflare R2 is the configured provider) because Render's filesystem
is ephemeral. Profile photos deliberately stay in PostgreSQL.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from urllib.parse import quote

from flask import current_app


class StorageError(RuntimeError):
    """Raised when uploaded-file storage is unavailable or misconfigured."""


def _clean_key(key):
    if not isinstance(key, str):
        raise StorageError('Storage key must be a string')
    if key.startswith(('/', '\\')):
        raise StorageError('Invalid storage key')
    key = key.replace('\\', '/').strip('/')
    parts = [part for part in key.split('/') if part]
    if not parts or any(part in {'.', '..'} for part in parts):
        raise StorageError('Invalid storage key')
    return '/'.join(parts)


class LocalStorage:
    """Filesystem backend for local development only."""

    def __init__(self, root):
        self.root = Path(root)

    def _path(self, key):
        key = _clean_key(key)
        path = (self.root / key).resolve()
        root = self.root.resolve()
        if path != root and root not in path.parents:
            raise StorageError('Invalid storage key')
        return path

    def save(self, key, data, content_type=None):
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read(self, key):
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(key)
        guessed_type = mimetypes.guess_type(path.name)[0]
        return path.read_bytes(), guessed_type or 'application/octet-stream'

    def delete(self, key):
        path = self._path(key)
        if path.is_file():
            path.unlink()
        return True

    def exists(self, key):
        return self._path(key).is_file()

    def url_for(self, key):
        return None


class S3Storage:
    """S3-compatible backend for Cloudflare R2, AWS S3, or similar."""

    def __init__(self, *, endpoint_url, bucket, region, access_key_id,
                 secret_access_key, public_base_url=''):
        self.endpoint_url = endpoint_url
        self.bucket = bucket
        self.region = region or 'auto'
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.public_base_url = (public_base_url or '').rstrip('/')
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        missing = [
            name for name, value in (
                ('S3_BUCKET', self.bucket),
                ('S3_ACCESS_KEY_ID', self.access_key_id),
                ('S3_SECRET_ACCESS_KEY', self.secret_access_key),
            )
            if not value
        ]
        if missing:
            raise StorageError(
                'S3 storage is missing: ' + ', '.join(missing)
            )
        try:
            import boto3
        except ImportError as error:
            raise StorageError('boto3 is required for S3 storage') from error
        self._client = boto3.client(
            's3',
            endpoint_url=self.endpoint_url or None,
            region_name=self.region,
            aws_access_key_id=self.access_key_id,
            aws_secret_access_key=self.secret_access_key,
        )
        return self._client

    def save(self, key, data, content_type=None):
        key = _clean_key(key)
        kwargs = {
            'Bucket': self.bucket,
            'Key': key,
            'Body': data,
        }
        if content_type:
            kwargs['ContentType'] = content_type
        self._get_client().put_object(**kwargs)
        return key

    @staticmethod
    def _is_not_found(error):
        if error.__class__.__name__ in {'NoSuchKey', '404'}:
            return True
        response = getattr(error, 'response', None) or {}
        code = (response.get('Error') or {}).get('Code')
        return code in {'404', 'NoSuchKey', 'NotFound'}

    def read(self, key):
        key = _clean_key(key)
        try:
            response = self._get_client().get_object(
                Bucket=self.bucket, Key=key
            )
        except StorageError:
            raise
        except Exception as error:
            if self._is_not_found(error):
                raise FileNotFoundError(key) from error
            raise StorageError('Could not read stored file') from error
        body = response['Body'].read()
        content_type = response.get('ContentType') or 'application/octet-stream'
        return body, content_type

    def delete(self, key):
        self._get_client().delete_object(Bucket=self.bucket, Key=_clean_key(key))
        return True

    def exists(self, key):
        client = self._get_client()
        try:
            client.head_object(Bucket=self.bucket, Key=_clean_key(key))
            return True
        except StorageError:
            raise
        except Exception as error:
            if self._is_not_found(error):
                return False
            raise StorageError('Could not check stored file') from error

    def url_for(self, key):
        if not self.public_base_url:
            return None
        return self.public_base_url + '/' + quote(_clean_key(key))


def get_storage():
    """Return the configured storage backend for the current app."""
    backend = (current_app.config.get('STORAGE_BACKEND') or 'local').lower()
    if backend == 'local':
        root = current_app.config.get('UPLOAD_FOLDER') or (
            Path(current_app.instance_path) / 'uploads'
        )
        return LocalStorage(root)
    if backend == 's3':
        return S3Storage(
            endpoint_url=current_app.config.get('S3_ENDPOINT_URL'),
            bucket=current_app.config.get('S3_BUCKET'),
            region=current_app.config.get('S3_REGION'),
            access_key_id=current_app.config.get('S3_ACCESS_KEY_ID'),
            secret_access_key=current_app.config.get('S3_SECRET_ACCESS_KEY'),
            public_base_url=current_app.config.get('S3_PUBLIC_BASE_URL'),
        )
    raise StorageError(f'Unknown STORAGE_BACKEND: {backend}')
