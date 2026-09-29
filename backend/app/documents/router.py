"""Uploaded Documents: a Student's photos of Documents no issuer holds digitally."""

import uuid
from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select

from app.auth.deps import CurrentStudent, SessionDep, SettingsDep
from app.config import Settings, get_settings
from app.documents import crypto
from app.documents.agent import DocumentAgent, UploadError, delete_document
from app.documents.links import InvalidLink, Viewer, create_link, read_link
from app.documents.reading import FACT_FOR_KIND, KIND_NAMES, Kind
from app.documents.storage import ObjectNotFound, ObjectStore, object_store
from app.models import AuditEvent, UploadedDocument, VerificationException
from app.sources.http import SourceHttp
from app.sources.registers import RegistersClient

router = APIRouter(tags=["documents"])

MAX_TEXT = 20_000


def get_object_store(settings: Annotated[Settings, Depends(get_settings)]) -> ObjectStore:
    return object_store(settings)


StoreDep = Annotated[ObjectStore, Depends(get_object_store)]


class UploadedDocumentOut(BaseModel):
    id: uuid.UUID
    kind: str
    name: str
    fact_name: str
    status: str
    fields: dict[str, Any]
    message: str | None = None
    remedy: str | None = None
    reviewer_note: str | None = None
    created_at: datetime


class UploadOut(BaseModel):
    readable: bool
    message: str
    problems: list[str]
    document: UploadedDocumentOut | None
    verified_facts: list[str]


class LinkOut(BaseModel):
    url: str
    expires_at: datetime


def document_out(
    document: UploadedDocument, exception: VerificationException | None
) -> UploadedDocumentOut:
    kind = Kind(document.kind)
    return UploadedDocumentOut(
        id=document.id,
        kind=kind.value,
        name=KIND_NAMES[kind],
        fact_name=FACT_FOR_KIND[kind],
        status=document.status,
        fields=document.fields,
        message=exception.message if exception else None,
        remedy=exception.remedy if exception else None,
        reviewer_note=exception.resolution if exception else None,
        created_at=document.created_at,
    )


async def _latest_exceptions(
    session, document_ids: list[uuid.UUID]
) -> dict[uuid.UUID, VerificationException]:
    rows = (
        await session.scalars(
            select(VerificationException)
            .where(VerificationException.uploaded_document_id.in_(document_ids))
            .order_by(VerificationException.created_at)
        )
    ).all()
    return {e.uploaded_document_id: e for e in rows if e.uploaded_document_id}


async def _own(session, student_id: uuid.UUID, document_id: uuid.UUID) -> UploadedDocument:
    document = await session.get(UploadedDocument, document_id)
    if document is None or document.student_id != student_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such document")
    return document


@router.post("/me/documents/uploads", status_code=status.HTTP_201_CREATED)
async def upload(
    student: CurrentStudent,
    session: SessionDep,
    settings: SettingsDep,
    http: SourceHttp,
    store: StoreDep,
    kind: Annotated[Kind, Form()],
    text: Annotated[str, Form(max_length=MAX_TEXT)],
    file: Annotated[UploadFile, File()],
) -> UploadOut:
    """Upload a photo of a Document, with the text the phone read from it.

    The text is used only to find the few fields a check needs, and is not kept.
    """
    data = await file.read(settings.document_max_bytes + 1)
    agent = DocumentAgent(session, settings, RegistersClient(http, settings), store)
    try:
        result = await agent.upload(student, kind, data, (file.content_type or "").lower(), text)
    except UploadError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    await session.commit()
    return UploadOut(
        readable=result.document is not None,
        message=result.message,
        problems=result.reading.problems,
        document=None
        if result.document is None
        else document_out(result.document, result.exception),
        verified_facts=[p.fact_name for p in result.proofs],
    )


@router.get("/me/documents/uploads")
async def my_uploads(student: CurrentStudent, session: SessionDep) -> list[UploadedDocumentOut]:
    documents = (
        await session.scalars(
            select(UploadedDocument)
            .where(UploadedDocument.student_id == student.id)
            .where(UploadedDocument.status.not_in(("deleted", "replaced")))
            .order_by(UploadedDocument.created_at.desc())
        )
    ).all()
    exceptions = await _latest_exceptions(session, [d.id for d in documents])
    return [document_out(d, exceptions.get(d.id)) for d in documents]


@router.get("/me/documents/uploads/{document_id}/link")
async def my_upload_link(
    document_id: uuid.UUID, student: CurrentStudent, session: SessionDep, settings: SettingsDep
) -> LinkOut:
    document = await _own(session, student.id, document_id)
    if document.object_key is None:
        raise HTTPException(status.HTTP_410_GONE, "This photo has been deleted")
    link = create_link(settings, document.id, Viewer("student", student.id))
    return LinkOut(url=link.path, expires_at=link.expires_at)


@router.delete("/me/documents/uploads/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(
    document_id: uuid.UUID, student: CurrentStudent, session: SessionDep, store: StoreDep
) -> None:
    document = await _own(session, student.id, document_id)
    await delete_document(session, store, document, "The Student deleted the photo")
    session.add(
        AuditEvent(
            actor_type="student",
            actor_id=student.id,
            action="document.delete",
            subject_type="uploaded_document",
            subject_id=document.id,
            detail={},
        )
    )
    await session.commit()


@router.get("/documents/{document_id}/content")
async def document_content(
    document_id: uuid.UUID,
    session: SessionDep,
    settings: SettingsDep,
    store: StoreDep,
    token: Annotated[str, Query()],
) -> Response:
    """The photo itself, through a link signed for one viewer that expires in minutes."""
    try:
        viewer = read_link(settings, document_id, token)
    except InvalidLink as error:
        raise HTTPException(status.HTTP_403_FORBIDDEN, str(error)) from error
    document = await session.get(UploadedDocument, document_id)
    if document is None or document.object_key is None:
        raise HTTPException(status.HTTP_410_GONE, "This photo has been deleted")
    try:
        blob = await store.get(document.object_key)
    except ObjectNotFound as error:
        raise HTTPException(status.HTTP_410_GONE, "This photo has been deleted") from error
    data = crypto.decrypt(settings, str(document.id), blob)
    if viewer.kind == "official":
        session.add(
            AuditEvent(
                actor_type="official",
                actor_id=viewer.id,
                action="document.view",
                subject_type="uploaded_document",
                subject_id=document.id,
                detail={},
            )
        )
        await session.commit()
    return Response(
        data,
        media_type=document.content_type,
        headers={
            "Cache-Control": "private, no-store",
            "Content-Disposition": "inline",
            "X-Content-Type-Options": "nosniff",
        },
    )
