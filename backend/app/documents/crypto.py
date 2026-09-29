"""Envelope encryption for Uploaded Documents.

Each photo is encrypted with its own random AES-256-GCM data key, and that key is wrapped with
the master key. The stored object carries everything needed to decrypt it except the master key,
and the document id is bound in as associated data, so an object cannot be passed off as another.
"""

import base64
import hashlib
import os
from functools import cache

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from app.config import Settings

MAGIC = b"PNK1"
_NONCE = 12
_WRAPPED = 32 + 16  # data key plus its GCM tag


class DecryptionError(Exception):
    pass


@cache
def _master_key(secret_key: str, configured: str | None) -> bytes:
    if configured:
        key = base64.b64decode(configured)
        if len(key) != 32:
            raise ValueError("PANKH_DOCUMENT_MASTER_KEY must be 32 bytes, base64-encoded")
        return key
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=b"pankh uploaded documents"
    ).derive(secret_key.encode())


def master_key(settings: Settings) -> bytes:
    return _master_key(settings.secret_key, settings.document_master_key)


def key_id(settings: Settings) -> str:
    return hashlib.sha256(master_key(settings)).hexdigest()[:16]


def encrypt(settings: Settings, document_id: str, data: bytes) -> bytes:
    aad = document_id.encode()
    data_key = AESGCM.generate_key(bit_length=256)
    wrap_nonce, data_nonce = os.urandom(_NONCE), os.urandom(_NONCE)
    wrapped = AESGCM(master_key(settings)).encrypt(wrap_nonce, data_key, aad)
    return (
        MAGIC + wrap_nonce + wrapped + data_nonce + AESGCM(data_key).encrypt(data_nonce, data, aad)
    )


def decrypt(settings: Settings, document_id: str, blob: bytes) -> bytes:
    if not blob.startswith(MAGIC):
        raise DecryptionError("Not an encrypted Pankh document")
    aad = document_id.encode()
    at = len(MAGIC)
    wrap_nonce = blob[at : at + _NONCE]
    wrapped = blob[at + _NONCE : at + _NONCE + _WRAPPED]
    rest = blob[at + _NONCE + _WRAPPED :]
    try:
        data_key = AESGCM(master_key(settings)).decrypt(wrap_nonce, wrapped, aad)
        return AESGCM(data_key).decrypt(rest[:_NONCE], rest[_NONCE:], aad)
    except Exception as error:
        raise DecryptionError("The document could not be decrypted") from error
