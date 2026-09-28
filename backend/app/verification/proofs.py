"""Signing Proofs so anyone can check them.

A Proof is a small JSON statement: this Fact about this Student was confirmed by this source
at this time. It is signed with Ed25519 over its canonical JSON form. The public key is
published, so a scholarship office can check a Proof without trusting Pankh's database.
"""

import base64
import hashlib
import json
from functools import cache
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from app.config import Settings


def canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


@cache
def _key_from_seed(seed: bytes) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(seed)


def signing_key(settings: Settings) -> Ed25519PrivateKey:
    """The configured key (32 bytes, base64), or in development one derived from secret_key."""
    if settings.proof_signing_key:
        return _key_from_seed(base64.b64decode(settings.proof_signing_key))
    return _key_from_seed(
        hashlib.sha256(b"pankh-proof-signing:" + settings.secret_key.encode()).digest()
    )


def public_key_bytes(settings: Settings) -> bytes:
    return signing_key(settings).public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)


def key_id(settings: Settings) -> str:
    return hashlib.sha256(public_key_bytes(settings)).hexdigest()[:16]


def sign(settings: Settings, payload: dict[str, Any]) -> str:
    return base64.urlsafe_b64encode(signing_key(settings).sign(canonical(payload))).decode()


def verify(public_key: bytes, payload: dict[str, Any], signature: str) -> bool:
    try:
        Ed25519PublicKey.from_public_bytes(public_key).verify(
            base64.urlsafe_b64decode(signature), canonical(payload)
        )
    except (InvalidSignature, ValueError):
        return False
    return True
