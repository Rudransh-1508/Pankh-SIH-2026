"""Ministry views: coverage of eligible students, and where applications stall."""

from collections import Counter, defaultdict
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.auth.deps import CurrentOfficial, SessionDep, SettingsDep
from app.coverage.service import compute_coverage, official_figures
from app.models import ApplicationSnapshot, AuditEvent, CoverageRun, Official
from app.sources.http import SourceHttp, SourceUnavailable
from app.sources.registers import RegistersClient
from app.sources.scholarship_systems import ScholarshipSystemsClient

router = APIRouter(prefix="/ministry", tags=["ministry"])


def _require(official: Official) -> None:
    if official.level not in ("ministry", "state"):
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Coverage is for state and ministry officials."
        )


def _for(official: Official, states: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return (
        states
        if official.level == "ministry"
        else [s for s in states if s["state"] == official.state]
    )


@router.post("/coverage/runs", status_code=status.HTTP_201_CREATED)
async def run_coverage(
    official: CurrentOfficial, session: SessionDep, settings: SettingsDep, http: SourceHttp
) -> dict[str, Any]:
    """Link the education registers against scholarship registrations now."""
    if official.level != "ministry":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the ministry can start a coverage run."
        )
    try:
        result = await compute_coverage(
            RegistersClient(http, settings), ScholarshipSystemsClient(http, settings)
        )
    except SourceUnavailable as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    run = CoverageRun(summary=result.summary, unreached=result.unreached)
    session.add(run)
    await session.flush()
    session.add(
        AuditEvent(
            actor_type="official",
            actor_id=official.id,
            action="coverage.run",
            subject_type="coverage_run",
            subject_id=run.id,
            detail={"totals": result.summary["totals"]},
        )
    )
    await session.commit()
    return {"id": str(run.id), "created_at": run.created_at.isoformat(), **result.summary}


async def _latest(session) -> CoverageRun:
    run = await session.scalar(select(CoverageRun).order_by(CoverageRun.created_at.desc()).limit(1))
    if run is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No coverage run yet. Start one.")
    return run


@router.get("/coverage")
async def coverage(official: CurrentOfficial, session: SessionDep) -> dict[str, Any]:
    _require(official)
    run = await _latest(session)
    states = _for(official, run.summary["states"])
    summary = run.summary | {"states": states}
    if official.level != "ministry":
        # Totals must describe what this official can see, not the whole country.
        keys = ("enrolled", "reached", "possible", "unreached")
        totals = {key: sum(state[key] for state in states) for key in keys}
        share = round(totals["reached"] / totals["enrolled"], 3) if totals["enrolled"] else 0.0
        summary["totals"] = totals | {"coverage": share}
    return {"id": str(run.id), "created_at": run.created_at.isoformat(), **summary}


@router.get("/coverage/unreached")
async def unreached(
    official: CurrentOfficial,
    session: SessionDep,
    state: str | None = None,
    district: str | None = None,
    limit: int = Query(200, ge=1, le=2000),
) -> dict[str, Any]:
    """Unreached Students, with the Schemes each could apply for, for outreach."""
    _require(official)
    if official.level == "state":
        state = official.state
    run = await _latest(session)
    rows = [
        r
        for r in run.unreached
        if (state is None or r["state"] == state)
        and (district is None or r["district"] == district)
    ]
    return {"total": len(rows), "items": rows[:limit]}


@router.get("/official-figures")
async def figures(official: CurrentOfficial) -> dict[str, Any]:
    """The ministry's published beneficiary figures, by state and year."""
    _require(official)
    rows = official_figures()
    if official.level == "state":
        rows = [r for r in rows if r["state"] == official.state]
    return {"rows": rows}


@router.get("/pipeline")
async def pipeline(
    official: CurrentOfficial, session: SessionDep, settings: SettingsDep, http: SourceHttp
) -> dict[str, Any]:
    """Where NSP applications sit now, by state, and stalls seen among Pankh users."""
    _require(official)
    systems = ScholarshipSystemsClient(http, settings)
    try:
        registrations, offset = [], 0
        while True:
            page = await systems.nsp_registrations(offset=offset)
            registrations += page["items"]
            offset += len(page["items"])
            if offset >= page["total"] or not page["items"]:
                break
    except SourceUnavailable as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    by_state: dict[str, Counter] = defaultdict(Counter)
    for registration in registrations:
        if official.level == "state" and registration["state"] != official.state:
            continue
        by_state[registration["state"]][registration["status"]] += 1
    waiting = (
        await session.execute(
            select(ApplicationSnapshot.waiting_on, func.count())
            .where(ApplicationSnapshot.waiting_on.is_not(None))
            .group_by(ApplicationSnapshot.waiting_on)
        )
    ).all()
    return {
        "states": [
            {"state": state, "total": sum(counts.values()), "statuses": dict(counts.most_common())}
            for state, counts in sorted(by_state.items())
        ],
        "waiting_on": {who: count for who, count in waiting},
    }
