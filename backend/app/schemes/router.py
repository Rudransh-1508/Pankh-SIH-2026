from fastapi import APIRouter, HTTPException, Query, status

import pankh_rules
from app.schemes.schemas import CitationOut, FactSpecOut, InstituteOut, SchemeOut, SourceOut

router = APIRouter(tags=["catalogue"])


@router.get("/schemes")
async def list_schemes() -> list[SchemeOut]:
    return [SchemeOut.of(scheme) for scheme in pankh_rules.SCHEMES.values()]


@router.get("/schemes/{scheme_id}")
async def get_scheme(scheme_id: str) -> SchemeOut:
    scheme = pankh_rules.SCHEMES.get(scheme_id)
    if scheme is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such scheme")
    return SchemeOut.of(scheme)


@router.get("/facts/schema")
async def fact_schema() -> list[FactSpecOut]:
    """Every Fact the Rules use, with labels, so clients can build forms from it."""
    return [FactSpecOut.of(spec) for spec in pankh_rules.fact_specs().values()]


@router.get("/sources")
async def list_sources() -> list[SourceOut]:
    return [
        SourceOut(
            id=source.id,
            title=source.title,
            url=source.url,
            sha256=source.sha256,
            pages=source.pages,
            issued=source.issued.isoformat() if source.issued else None,
            effective=source.effective.isoformat() if source.effective else None,
        )
        for source in pankh_rules.sources().values()
    ]


@router.get("/institutes/top-class")
async def search_top_class_institutes(
    q: str = Query("", max_length=100, description="Words to match in name, location or state"),
    limit: int = Query(20, ge=1, le=265),
) -> list[InstituteOut]:
    matches = pankh_rules.search_top_class(q, limit)
    return [
        InstituteOut(
            id=i.id,
            name=i.name,
            location=i.location,
            state=i.state,
            courses=i.courses,
            citation=CitationOut.of(i.citation),
        )
        for i in matches
    ]
