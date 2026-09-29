"""Rule authoring: check a new Guideline against the Rules, and approve the changes it makes."""

import hashlib
import io
import uuid
from datetime import date, datetime
from typing import Annotated, Literal

import pdfplumber
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy import select

import pankh_rules
from app.auth.deps import CurrentOfficial, SessionDep
from app.models import AuditEvent, Official, RuleDraft
from pankh_rules.authoring import draft_changes, parameters, patched

router = APIRouter(prefix="/ministry/rule-drafts", tags=["rule authoring"])

MAX_PDF_BYTES = 20 * 1024 * 1024


class DraftOut(BaseModel):
    id: uuid.UUID
    scheme_id: str
    scheme: str
    parameter: str
    description: str
    unit: str
    current_value: float
    found_value: float
    source_title: str
    page: int
    excerpt: str
    status: str
    effective_from: date | None
    note: str | None
    created_at: datetime


class DecisionIn(BaseModel):
    decision: Literal["approve", "reject"]
    effective_from: date | None = None
    note: str = ""


def _ministry(official: Official) -> None:
    if official.level != "ministry":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rules are changed by the ministry.")


def _out(d: RuleDraft) -> DraftOut:
    return DraftOut(
        id=d.id,
        scheme_id=d.scheme_id,
        scheme=pankh_rules.SCHEMES[d.scheme_id].short_name,
        parameter=d.parameter,
        description=d.description,
        unit=d.unit,
        current_value=d.current_value,
        found_value=d.found_value,
        source_title=d.source_title,
        page=d.page,
        excerpt=d.excerpt,
        status=d.status,
        effective_from=d.effective_from,
        note=d.note,
        created_at=d.created_at,
    )


def _pages(data: bytes) -> list[str]:
    try:
        with pdfplumber.open(io.BytesIO(data)) as pdf:
            return [page.extract_text() or "" for page in pdf.pages]
    except Exception as error:  # pdfplumber raises many kinds of errors for broken files
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "That PDF could not be read."
        ) from error


@router.post("", status_code=status.HTTP_201_CREATED)
async def check_guideline(
    official: CurrentOfficial,
    session: SessionDep,
    scheme_id: Annotated[str, Form()],
    title: Annotated[str, Form(min_length=3, max_length=200)],
    file: Annotated[UploadFile, File()],
) -> list[DraftOut]:
    """Read a Guideline PDF and draft a change for every figure that differs from the Rules."""
    _ministry(official)
    if scheme_id not in pankh_rules.SCHEMES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown scheme.")
    data = await file.read(MAX_PDF_BYTES + 1)
    if len(data) > MAX_PDF_BYTES or not data.startswith(b"%PDF-"):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Upload the Guideline as a PDF under 20 MB."
        )
    pages = _pages(data)
    if not any(text.strip() for text in pages):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "This PDF has no text layer (it is a scan). Ask for the text version.",
        )
    digest = hashlib.sha256(data).hexdigest()
    drafts = [
        RuleDraft(
            created_by=official.id,
            scheme_id=scheme_id,
            parameter=d.parameter.path,
            description=d.parameter.description,
            unit=d.parameter.unit,
            current_value=float(d.parameter.value),
            found_value=d.figure.value,
            source_title=title.strip(),
            source_sha256=digest,
            page=d.figure.page,
            excerpt=d.figure.excerpt[:2000],
            status="proposed" if d.changed else "matches",
        )
        for d in draft_changes(scheme_id, pages)
    ]
    session.add_all(drafts)
    await session.flush()
    session.add(
        AuditEvent(
            actor_type="official",
            actor_id=official.id,
            action="guideline.check",
            subject_type="official",
            subject_id=official.id,
            detail={"scheme": scheme_id, "title": title, "sha256": digest, "drafts": len(drafts)},
        )
    )
    await session.commit()
    return [_out(d) for d in drafts]


@router.get("")
async def drafts(official: CurrentOfficial, session: SessionDep) -> list[DraftOut]:
    _ministry(official)
    rows = (
        await session.scalars(select(RuleDraft).order_by(RuleDraft.created_at.desc()).limit(200))
    ).all()
    return [_out(d) for d in rows]


async def _draft(session, draft_id: uuid.UUID) -> RuleDraft:
    draft = await session.get(RuleDraft, draft_id)
    if draft is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such draft")
    return draft


@router.post("/{draft_id}/decision")
async def decide(
    draft_id: uuid.UUID, body: DecisionIn, official: CurrentOfficial, session: SessionDep
) -> DraftOut:
    _ministry(official)
    draft = await _draft(session, draft_id)
    if draft.status != "proposed":
        raise HTTPException(status.HTTP_409_CONFLICT, "This draft has already been decided.")
    if body.decision == "approve":
        if body.effective_from is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Say from when the change applies."
            )
        parameter = next((p for p in parameters() if p.path == draft.parameter), None)
        if parameter is None:
            raise HTTPException(status.HTTP_409_CONFLICT, "That Parameter no longer exists.")
        if body.effective_from <= parameter.since:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT,
                f"The change must apply after the current value's date ({parameter.since}).",
            )
        draft.patch = patched(
            parameter,
            draft.found_value,
            body.effective_from,
            f"{draft.source_title}, page {draft.page}",
        )
        draft.effective_from = body.effective_from
    draft.status = "approved" if body.decision == "approve" else "rejected"
    draft.decided_by = official.id
    draft.note = body.note.strip() or None
    session.add(
        AuditEvent(
            actor_type="official",
            actor_id=official.id,
            action=f"rule_draft.{body.decision}",
            subject_type="rule_draft",
            subject_id=draft.id,
            detail={"parameter": draft.parameter, "value": draft.found_value},
        )
    )
    await session.commit()
    return _out(draft)


@router.get("/{draft_id}/patch", response_class=PlainTextResponse)
async def patch(draft_id: uuid.UUID, official: CurrentOfficial, session: SessionDep) -> str:
    """The Parameter file as the approved change leaves it, for the rules repository."""
    _ministry(official)
    draft = await _draft(session, draft_id)
    if draft.patch is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Only an approved draft has a change.")
    return draft.patch
