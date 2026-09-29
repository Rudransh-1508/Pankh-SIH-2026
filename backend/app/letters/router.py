"""The deficiency agent's request letters, filled from the Student's own records."""

import uuid
from collections import defaultdict
from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel

import pankh_rules
from app.academic_year import current_academic_year
from app.auth.deps import CurrentStudent, SessionDep
from app.facts.service import current_facts
from app.letters.texts import BLANK, CLOSING, LETTERS
from app.models import Identity, VerificationException
from pankh_rules.engine import format_inr

router = APIRouter(prefix="/me/letters", tags=["letters"])

_DOCUMENTS = {"en": "caste certificate", "hi": "जाति प्रमाण पत्र"}


class LetterOut(BaseModel):
    kind: str
    language: str
    title: str
    to: str
    subject: str
    body: str
    closing: str

    @property
    def text(self) -> str:
        return "\n\n".join((self.to, f"Subject: {self.subject}", self.body, self.closing))


@router.get("/{kind}")
async def letter(
    kind: str,
    student: CurrentStudent,
    session: SessionDep,
    language: Literal["en", "hi"] = "en",
    issue: uuid.UUID | None = None,
    scheme_id: Annotated[str | None, Query(max_length=32)] = None,
    application: Annotated[str | None, Query(max_length=40)] = None,
    reason: Annotated[str | None, Query(max_length=300)] = None,
) -> LetterOut:
    """A request letter of one kind. Details Pankh does not know are left as blanks to fill in."""
    templates = LETTERS.get(kind)
    if templates is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such letter")
    template = templates[language]
    identity = await session.get(Identity, student.id)
    facts = await current_facts(session, student.id)
    year = current_academic_year()
    scheme = pankh_rules.SCHEMES.get(scheme_id or "") or pankh_rules.SCHEMES.get(
        str(facts.get("current_mota_award"))
    )
    values: dict[str, str] = defaultdict(lambda: BLANK)
    values |= {
        "name": identity.name if identity else BLANK,
        "district": (identity.district if identity else None) or BLANK,
        "state": (identity.state if identity else None) or BLANK,
        "phone": student.phone,
        "financial_year": f"{year - 1}-{year % 100:02d}",
        "scheme": scheme.short_name if scheme else "Post-Matric",
        "application": application or "",
        "reason": (reason or "").strip(),
        "document": _DOCUMENTS[language],
    }
    if isinstance(facts.get("family_income"), int | float):
        values["income"] = format_inr(facts["family_income"]).lstrip("₹")
    if issue is not None:
        exception = await session.get(VerificationException, issue)
        if exception is None or exception.student_id != student.id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "No such issue")
        evidence = exception.evidence or {}
        values["name_on_document"] = evidence.get("name_on_document") or BLANK
        values["issuer"] = evidence.get("issuer") or BLANK
    closing = CLOSING[language].format_map(values | {"date": date.today().strftime("%d/%m/%Y")})
    return LetterOut(
        kind=kind,
        language=language,
        title=template["title"],
        to=template["to"].format_map(values),
        subject=template["subject"].format_map(values),
        body=" ".join(template["body"].format_map(values).split()),
        closing=closing,
    )
