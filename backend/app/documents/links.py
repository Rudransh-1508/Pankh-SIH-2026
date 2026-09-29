"""Short-lived links to an Uploaded Document, signed for one viewer."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

import jwt

from app.config import Settings

ALGORITHM = "HS256"
AUDIENCE = "pankh-document"


class InvalidLink(Exception):
    pass


@dataclass(frozen=True)
class Viewer:
    kind: str  # student | official
    id: uuid.UUID


@dataclass(frozen=True)
class Link:
    path: str
    expires_at: datetime


def create_link(settings: Settings, document_id: uuid.UUID, viewer: Viewer) -> Link:
    expires_at = datetime.now(UTC) + settings.document_link_ttl
    token = jwt.encode(
        {
            "doc": str(document_id),
            "sub": f"{viewer.kind}:{viewer.id}",
            "aud": AUDIENCE,
            "exp": expires_at,
        },
        settings.secret_key,
        algorithm=ALGORITHM,
    )
    return Link(f"/v1/documents/{document_id}/content?token={token}", expires_at)


def read_link(settings: Settings, document_id: uuid.UUID, token: str) -> Viewer:
    try:
        claims = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM], audience=AUDIENCE)
        if claims["doc"] != str(document_id):
            raise InvalidLink("This link is for another document")
        kind, _, viewer_id = claims["sub"].partition(":")
        return Viewer(kind, uuid.UUID(viewer_id))
    except (jwt.PyJWTError, KeyError, ValueError) as error:
        raise InvalidLink("This link has expired. Open the document again.") from error
