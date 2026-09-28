"""Government registers that confirm single Facts: e-District, AISHE, UDISE+, APAAR, UGC-NTA
and the NPCI Aadhaar mapper.

Each follows the shape of the real service's lookup: one identifier in, one record out.
Records are derived from the synthetic population, including its gaps and inconsistencies.
"""

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from pydantic import BaseModel

from pankh_simulators.population import Person, population

API_KEY = "pankh-simulator-key"


def require_api_key(x_api_key: Annotated[str | None, Header()] = None) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "A valid X-API-Key header is required")


router = APIRouter(dependencies=[Depends(require_api_key)])


def _not_found(what: str) -> HTTPException:
    return HTTPException(status.HTTP_404_NOT_FOUND, f"No {what} with that identifier")


def caste_certificate_number(person: Person) -> str:
    return hashlib.sha256(f"{person.id}:CSCER".encode()).hexdigest()[:10].upper()


@router.get("/edistrict/{state_code}/certificates/{number}", tags=["e-District"])
async def verify_certificate(state_code: str, number: str) -> dict:
    """Verify a caste certificate by its number, as state e-District portals allow."""
    for person in population().people:
        if (
            person.has_caste_certificate
            and person.state.code == state_code.upper()
            and caste_certificate_number(person) == number.upper()
        ):
            assert person.tribe is not None
            return {
                "certificate_number": number.upper(),
                "type": "Caste Certificate",
                "status": "VALID",
                "holder_name": person.caste_certificate_spelling,
                "category": "ST",
                "caste": person.tribe.name,
                "pvtg": person.tribe.pvtg,
                "district": person.district,
                "state": person.state.name,
            }
    raise _not_found("certificate")


@router.get("/aishe/institutions/{code}", tags=["AISHE"])
async def aishe_institution(code: str) -> dict:
    institution = population().institutions.get(code)
    if institution is None or institution.kind == "school":
        raise _not_found("institution")
    return {
        "aishe_code": institution.code,
        "name": institution.name,
        "type": institution.kind,
        "state": institution.state,
        "district": institution.district,
        "management": institution.management,
        "ugc_2f_12b": institution.fellowship_eligible,
        "recognised": institution.recognised,
    }


@router.get("/udise/schools/{code}", tags=["UDISE+"])
async def udise_school(code: str) -> dict:
    institution = population().institutions.get(code)
    if institution is None or institution.kind != "school":
        raise _not_found("school")
    return {
        "udise_code": institution.code,
        "name": institution.name,
        "state": institution.state,
        "district": institution.district,
        "management": institution.management,
        "recognised": institution.recognised,
    }


@router.get("/udise/students", tags=["UDISE+"])
async def udise_students(
    state: str | None = None,
    district: str | None = None,
    social_category: str | None = Query(None, pattern="^(ST|SC|OBC|GEN)$"),
    offset: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=1000),
) -> dict:
    """The enrolment roster schools report to UDISE+, which is how unreached students are found."""
    rows = [
        p
        for p in population().people
        if p.enrolled_in_udise
        and p.institution is not None
        and (state is None or p.state.name == state)
        and (district is None or p.district == district)
        and (social_category is None or (social_category == "ST") == p.is_scheduled_tribe)
    ]
    page = rows[offset : offset + limit]
    return {
        "total": len(rows),
        "items": [
            {
                "student_ref": f"UD-{p.id}",
                "name": p.name_hi if int(p.id[1:]) % 3 == 0 else p.name,
                "gender": p.gender,
                "date_of_birth": p.date_of_birth.isoformat(),
                "social_category": "ST" if p.is_scheduled_tribe else "GEN",
                "class": p.education_level.removeprefix("class_"),
                "udise_code": p.institution.code if p.institution else "",
                "district": p.district,
                "state": p.state.name,
            }
            for p in page
        ],
    }


@router.get("/apaar/students/{apaar_id}", tags=["APAAR"])
async def apaar_student(apaar_id: str) -> dict:
    person = population().by_apaar_id(apaar_id)
    if person is None:
        raise _not_found("student")
    return {
        "apaar_id": person.apaar_id,
        "name": person.name,
        "date_of_birth": person.date_of_birth.isoformat(),
        "gender": person.gender,
        "current_enrolment": None
        if person.institution is None
        else {
            "institution_code": person.institution.code,
            "institution_name": person.institution.name,
            "level": person.education_level,
        },
        "results": [
            {"level": level, "percentage": percentage}
            for level, percentage in (
                ("bachelors", person.bachelors_percent),
                ("masters", person.masters_percent),
            )
            if percentage is not None
        ],
    }


@router.get("/nta/net-results/{roll_number}", tags=["UGC-NTA"])
async def net_result(roll_number: str) -> dict:
    person = population().by_net_roll_number(roll_number)
    if person is None:
        raise _not_found("result")
    return {
        "roll_number": roll_number,
        "candidate_name": person.name,
        "date_of_birth": person.date_of_birth.isoformat(),
        "result": person.net_result or "NOT QUALIFIED",
        "qualified": person.net_result is not None,
    }


class SeedingQuery(BaseModel):
    reference_key: str


@router.post("/npci/aadhaar-seeding", tags=["NPCI"])
async def aadhaar_seeding(query: SeedingQuery) -> dict:
    """Whether a bank account is linked to the person's Aadhaar for direct benefit transfer."""
    person = population().by_uid_token(query.reference_key)
    if person is None:
        raise _not_found("person")
    return {
        "seeded": person.bank_seeded,
        "bank": "State Bank of India" if person.bank_seeded else None,
        "mapped_on": "2024-02-11" if person.bank_seeded else None,
    }
