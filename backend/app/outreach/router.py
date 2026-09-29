"""Outreach campaigns for Unreached Students, and the lists schools receive."""

import uuid
from collections import Counter
from datetime import UTC, datetime
from html import escape
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select

import pankh_rules
from app.auth.deps import CurrentOfficial, SessionDep, SettingsDep
from app.auth.sms import SmsSender, get_sms_sender
from app.models import AuditEvent, Campaign, CampaignTarget, CoverageRun, Official, OutreachLink
from app.outreach import service
from app.sources.http import SourceHttp, SourceUnavailable
from app.sources.registers import RegistersClient

router = APIRouter(prefix="/outreach", tags=["outreach"])
SmsDep = Annotated[SmsSender, Depends(get_sms_sender)]


class CampaignIn(BaseModel):
    state: str | None = None
    district: str | None = None
    channel: Literal["school", "family"]
    language: Literal["en", "hi"] = "en"


class MessageOut(BaseModel):
    to: str
    school: str | None
    students: int
    text: str


class CampaignOut(BaseModel):
    id: uuid.UUID
    state: str
    district: str | None
    channel: str
    language: str
    status: str
    created_at: datetime
    sent_at: datetime | None
    students: int
    schools: int
    delivery: dict[str, int]
    applied_since: int | None
    """Targets no longer unreached in a coverage run after sending; None until there is one."""
    preview: list[MessageOut] = []
    skipped_recent: int = 0


def _scope(official: Official, state: str | None, district: str | None) -> tuple[str, str | None]:
    match official.level:
        case "ministry":
            if not state:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Choose a state.")
            return state, district
        case "state":
            return official.state or "", district
        case "district":
            return official.state or "", official.district
    raise HTTPException(
        status.HTTP_403_FORBIDDEN, "Outreach is run by district, state and ministry officials."
    )


def _visible(official: Official, campaign: Campaign) -> bool:
    if official.level == "ministry":
        return True
    if official.level == "state":
        return campaign.state == official.state
    return campaign.state == official.state and campaign.district == official.district


async def _latest_run(session) -> CoverageRun:
    run = await session.scalar(select(CoverageRun).order_by(CoverageRun.created_at.desc()).limit(1))
    if run is None:
        raise HTTPException(
            status.HTTP_409_CONFLICT, "There is no coverage run yet. The ministry starts one."
        )
    return run


async def _out(
    session, campaign: Campaign, preview: list[MessageOut] | None = None, skipped: int = 0
) -> CampaignOut:
    targets = (
        await session.scalars(
            select(CampaignTarget).where(CampaignTarget.campaign_id == campaign.id)
        )
    ).all()
    applied_since = None
    if campaign.sent_at is not None:
        latest = await _latest_run(session)
        if latest.created_at > campaign.sent_at:
            still = {row["student_ref"] for row in latest.unreached}
            applied_since = sum(
                1 for t in targets if t.status == "sent" and t.student_ref not in still
            )
    return CampaignOut(
        id=campaign.id,
        state=campaign.state,
        district=campaign.district,
        channel=campaign.channel,
        language=campaign.language,
        status=campaign.status,
        created_at=campaign.created_at,
        sent_at=campaign.sent_at,
        students=len(targets),
        schools=len({t.udise_code for t in targets}),
        delivery=dict(Counter(t.status for t in targets)),
        applied_since=applied_since,
        preview=preview or [],
        skipped_recent=skipped,
    )


async def _preview(campaign: Campaign, run: CoverageRun, session, registers, settings):
    refs = set(
        (
            await session.scalars(
                select(CampaignTarget.student_ref).where(CampaignTarget.campaign_id == campaign.id)
            )
        ).all()
    )
    rows = [row for row in run.unreached if row["student_ref"] in refs]
    drafted = await service.messages(session, campaign, rows, registers, settings, limit=3)
    return [
        MessageOut(to=m.to, school=m.school, students=len(m.about), text=m.text) for m in drafted
    ]


async def _campaign(session, official: Official, campaign_id: uuid.UUID) -> Campaign:
    campaign = await session.get(Campaign, campaign_id)
    if campaign is None or not _visible(official, campaign):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No such campaign")
    return campaign


@router.post("/campaigns", status_code=status.HTTP_201_CREATED)
async def create_campaign(
    body: CampaignIn,
    official: CurrentOfficial,
    session: SessionDep,
    settings: SettingsDep,
    http: SourceHttp,
) -> CampaignOut:
    """Draft a campaign from the latest coverage run. Nothing is sent until it is approved."""
    state, district = _scope(official, body.state, body.district)
    run = await _latest_run(session)
    rows = service.unreached_rows(run, state, district)
    recent = await service.recently_messaged(session, body.channel)
    fresh = [row for row in rows if row["student_ref"] not in recent]
    if not fresh:
        where = f"{district}, {state}" if district else state
        reason = "everyone there was messaged recently" if rows else "none are unreached"
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"No students to contact in {where}: {reason}."
        )
    campaign = Campaign(
        created_by=official.id,
        coverage_run_id=run.id,
        state=state,
        district=district,
        channel=body.channel,
        language=body.language,
        status="draft",
    )
    session.add(campaign)
    await session.flush()
    session.add_all(
        CampaignTarget(
            campaign_id=campaign.id,
            student_ref=row["student_ref"],
            udise_code=row["udise_code"],
            district=row["district"],
            status="pending",
        )
        for row in fresh
    )
    await session.flush()
    try:
        preview = await _preview(campaign, run, session, RegistersClient(http, settings), settings)
    except SourceUnavailable as error:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, str(error)) from error
    await session.commit()
    return await _out(session, campaign, preview, skipped=len(rows) - len(fresh))


@router.get("/campaigns")
async def campaigns(official: CurrentOfficial, session: SessionDep) -> list[CampaignOut]:
    rows = (
        await session.scalars(select(Campaign).order_by(Campaign.created_at.desc()).limit(100))
    ).all()
    return [await _out(session, c) for c in rows if _visible(official, c)]


@router.get("/campaigns/{campaign_id}")
async def campaign(
    campaign_id: uuid.UUID,
    official: CurrentOfficial,
    session: SessionDep,
    settings: SettingsDep,
    http: SourceHttp,
) -> CampaignOut:
    found = await _campaign(session, official, campaign_id)
    run = await session.get(CoverageRun, found.coverage_run_id)
    preview = []
    if found.status == "draft" and run is not None:
        preview = await _preview(found, run, session, RegistersClient(http, settings), settings)
    return await _out(session, found, preview)


@router.post("/campaigns/{campaign_id}/send")
async def send_campaign(
    campaign_id: uuid.UUID,
    official: CurrentOfficial,
    session: SessionDep,
    settings: SettingsDep,
    http: SourceHttp,
    sms: SmsDep,
) -> CampaignOut:
    """Approve and send every message in the campaign."""
    found = await _campaign(session, official, campaign_id)
    if found.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "This campaign has already been decided.")
    run = await session.get(CoverageRun, found.coverage_run_id)
    assert run is not None
    found.status = "sent"
    found.approved_by = official.id
    found.sent_at = datetime.now(UTC)
    counts = await service.send(session, found, run, RegistersClient(http, settings), sms, settings)
    session.add(
        AuditEvent(
            actor_type="official",
            actor_id=official.id,
            action="campaign.send",
            subject_type="campaign",
            subject_id=found.id,
            detail={"channel": found.channel, "delivery": counts},
        )
    )
    await session.commit()
    return await _out(session, found)


@router.post("/campaigns/{campaign_id}/cancel")
async def cancel_campaign(
    campaign_id: uuid.UUID, official: CurrentOfficial, session: SessionDep
) -> CampaignOut:
    found = await _campaign(session, official, campaign_id)
    if found.status != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "This campaign has already been decided.")
    found.status = "cancelled"
    await session.commit()
    return await _out(session, found)


_LIST_PAGE = """<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ margin: 0; font-family: 'Noto Sans', 'Noto Sans Devanagari', system-ui, sans-serif;
    color: #1B2A4A; background: #F5F7F6; }}
  main {{ max-width: 860px; margin: 0 auto; padding: 24px 16px 48px; }}
  h1 {{ font-size: 24px; margin: 0 0 4px; }}
  p {{ line-height: 1.5; }}
  .muted {{ color: #52607a; font-size: 14px; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff; border-radius: 12px;
    overflow: hidden; margin-top: 16px; }}
  th, td {{ text-align: left; padding: 10px 12px; border-bottom: 1px solid #dfe5e3;
    font-size: 15px; vertical-align: top; }}
  th {{ background: #e6f1f2; font-size: 13px; text-transform: uppercase; letter-spacing: .03em; }}
  @media print {{ body {{ background: #fff; }} }}
</style></head>
<body><main>{body}</main></body></html>"""

_LIST_TEXT = {
    "en": {
        "title": "Students who may qualify for a scholarship",
        "intro": "These Scheduled Tribe students at {school} appear in UDISE+ but have not "
        "applied for a scholarship they may qualify for. Please help them apply; it is free.",
        "cols": ("Name", "Class", "May qualify for"),
        "checks": "Before applying, check each student's: {checks}.",
        "footer": "From Pankh, for the Ministry of Tribal Affairs. Keep this list private: it "
        "is for helping these students apply, and the link stops working after 30 days.",
    },
    "hi": {
        "title": "छात्रवृत्ति के संभावित पात्र विद्यार्थी",
        "intro": "{school} के ये अनुसूचित जनजाति विद्यार्थी UDISE+ में दर्ज हैं, पर उन्होंने उस "
        "छात्रवृत्ति के लिए आवेदन नहीं किया है जिसके वे पात्र हो सकते हैं। कृपया उन्हें आवेदन में "
        "मदद करें; आवेदन निःशुल्क है।",
        "cols": ("नाम", "कक्षा", "संभावित योजना"),
        "checks": "आवेदन से पहले हर विद्यार्थी की जाँच करें: {checks}।",
        "footer": "पंख की ओर से, जनजातीय कार्य मंत्रालय के लिए। यह सूची निजी रखें: यह केवल इन "
        "विद्यार्थियों को आवेदन में मदद के लिए है, और लिंक 30 दिन बाद काम नहीं करेगा।",
    },
}


# What a school checks before helping a student apply, in a few words each.
_CHECKS = {
    "family_income": ("family income", "परिवार की आय"),
    "has_aadhaar_seeded_bank_account": (
        "a bank account linked to Aadhaar",
        "आधार से जुड़ा बैंक खाता",
    ),
    "holds_other_scholarship": ("no other scholarship", "कोई अन्य छात्रवृत्ति नहीं"),
    "current_mota_award": (
        "no current MoTA scholarship",
        "अभी कोई जनजातीय कार्य मंत्रालय छात्रवृत्ति नहीं",
    ),
    "institution_recognised": ("a recognised school", "मान्यता प्राप्त विद्यालय"),
    "school_government_aided_or_local_body": (
        "a government or aided school (for NMMSS)",
        "सरकारी या सहायता प्राप्त विद्यालय (NMMSS के लिए)",
    ),
    "selected_in_nmms_exam": ("NMMS exam result (for NMMSS)", "NMMS परीक्षा परिणाम (NMMSS के लिए)"),
    "repeating_stage_in_other_subject": (
        "not repeating a class already passed",
        "पास की हुई कक्षा दोबारा नहीं",
    ),
    "admitted_to_top_class_institute": (
        "admission to a Top Class institute",
        "टॉप क्लास संस्थान में प्रवेश",
    ),
}


def _checks(rows: list[dict], language: str) -> list[str]:
    names = {f for row in rows for scheme in row["likely_schemes"] for f in scheme["to_confirm"]}
    specs = pankh_rules.fact_specs()
    index = 0 if language == "en" else 1
    return [
        _CHECKS[name][index] if name in _CHECKS else specs[name].label
        for name in sorted(names)
        if name in _CHECKS or name in specs
    ]


def _list_row(row: dict) -> str:
    schemes = ", ".join(dict.fromkeys(s["scheme"] for s in row["likely_schemes"]))
    return (
        f"<tr><td>{escape(row['name'])}</td><td>{escape(str(row['class']))}</td>"
        f"<td>{escape(schemes)}</td></tr>"
    )


@router.get("/l/{code}", response_class=HTMLResponse)
async def school_list(
    code: str, session: SessionDep, settings: SettingsDep, http: SourceHttp
) -> str:
    """The list a school nodal officer opens from their message. No sign-in: the code is for one
    school and one campaign, and stops working 30 days after sending."""
    link = await session.get(OutreachLink, code)
    found = await session.get(Campaign, link.campaign_id) if link else None
    run = await session.get(CoverageRun, found.coverage_run_id) if found else None
    if (
        link is None
        or found is None
        or run is None
        or found.status != "sent"
        or found.sent_at is None
        or datetime.now(UTC) > found.sent_at + service.LIST_TTL
    ):
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "This list is not available. Ask the district office for a new one.",
        )
    school_code = link.udise_code
    refs = set(
        (
            await session.scalars(
                select(CampaignTarget.student_ref)
                .where(CampaignTarget.campaign_id == found.id)
                .where(CampaignTarget.udise_code == school_code)
            )
        ).all()
    )
    rows = [r for r in run.unreached if r["student_ref"] in refs]
    school = await RegistersClient(http, settings).udise_school(school_code)
    text = _LIST_TEXT[found.language]
    name = escape(school["name"] if school else school_code)
    body_rows = "".join(
        _list_row(r) for r in sorted(rows, key=lambda r: (str(r["class"]), r["name"]))
    )
    head = "".join(f"<th>{c}</th>" for c in text["cols"])
    checks = text["checks"].format(checks=", ".join(_checks(rows, found.language)))
    body = (
        f"<h1>{text['title']}</h1><p class='muted'>{name} · {escape(school_code)}</p>"
        f"<p>{text['intro'].format(school=name)}</p>"
        f"<p class='muted'>{escape(checks)}</p>"
        f"<table><thead><tr>{head}</tr></thead><tbody>{body_rows}</tbody></table>"
        f"<p class='muted'>{text['footer']}</p>"
    )
    return _LIST_PAGE.format(lang=found.language, title=text["title"], body=body)
