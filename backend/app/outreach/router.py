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
from app.languages import Language
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
    language: Language = "en"


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
    "bn": {
        "title": "বৃত্তির সম্ভাব্য যোগ্য ছাত্রছাত্রী",
        "intro": "{school}-এর এই তফসিলি উপজাতি ছাত্রছাত্রীরা UDISE+-এ নথিভুক্ত, কিন্তু যে বৃত্তির "
        "যোগ্য হতে পারে তার জন্য আবেদন করেনি। অনুগ্রহ করে তাদের আবেদন করতে সাহায্য করুন; আবেদন "
        "বিনামূল্যে।",
        "cols": ("নাম", "শ্রেণি", "সম্ভাব্য প্রকল্প"),
        "checks": "আবেদনের আগে প্রত্যেক ছাত্রছাত্রীর যাচাই করুন: {checks}।",
        "footer": "পঙ্খের পক্ষ থেকে, জনজাতি বিষয়ক মন্ত্রকের জন্য। এই তালিকা গোপন রাখুন: এটি শুধু "
        "এই ছাত্রছাত্রীদের আবেদনে সাহায্যের জন্য, এবং লিংকটি 30 দিন পরে আর কাজ করবে না।",
    },
    "gu": {
        "title": "શિષ્યવૃત્તિ માટે સંભવિત પાત્ર વિદ્યાર્થીઓ",
        "intro": "{school}ના આ અનુસૂચિત જનજાતિ વિદ્યાર્થીઓ UDISE+માં નોંધાયેલા છે, પણ જે "
        "શિષ્યવૃત્તિ માટે તેઓ પાત્ર હોઈ શકે તેની અરજી કરી નથી. કૃપા કરીને તેમને અરજી કરવામાં મદદ "
        "કરો; અરજી મફત છે.",
        "cols": ("નામ", "ધોરણ", "સંભવિત યોજના"),
        "checks": "અરજી પહેલાં દરેક વિદ્યાર્થીની આ બાબતો તપાસો: {checks}.",
        "footer": "પંખ તરફથી, આદિજાતિ બાબતોના મંત્રાલય માટે. આ યાદી ખાનગી રાખો: તે ફક્ત આ "
        "વિદ્યાર્થીઓને અરજીમાં મદદ માટે છે, અને લિંક 30 દિવસ પછી કામ નહીં કરે.",
    },
    "mr": {
        "title": "शिष्यवृत्तीसाठी संभाव्य पात्र विद्यार्थी",
        "intro": "{school} मधील हे अनुसूचित जमातीचे विद्यार्थी UDISE+ मध्ये नोंदलेले आहेत, पण ज्या "
        "शिष्यवृत्तीसाठी ते पात्र असू शकतात तिचा अर्ज त्यांनी केलेला नाही. कृपया त्यांना अर्ज "
        "करण्यास मदत करा; अर्ज विनामूल्य आहे.",
        "cols": ("नाव", "इयत्ता", "संभाव्य योजना"),
        "checks": "अर्ज करण्यापूर्वी प्रत्येक विद्यार्थ्याचे हे तपासा: {checks}.",
        "footer": "पंखकडून, आदिवासी कार्य मंत्रालयासाठी. ही यादी गोपनीय ठेवा: ती फक्त या "
        "विद्यार्थ्यांना अर्ज करण्यास मदत करण्यासाठी आहे, आणि लिंक 30 दिवसांनंतर चालणार नाही.",
    },
    "or": {
        "title": "ଛାତ୍ରବୃତ୍ତି ପାଇଁ ସମ୍ଭାବ୍ୟ ଯୋଗ୍ୟ ଛାତ୍ରଛାତ୍ରୀ",
        "intro": "{school}ର ଏହି ଅନୁସୂଚିତ ଜନଜାତି ଛାତ୍ରଛାତ୍ରୀମାନେ UDISE+ରେ ପଞ୍ଜୀକୃତ, କିନ୍ତୁ ଯେଉଁ "
        "ଛାତ୍ରବୃତ୍ତି ପାଇଁ ସେମାନେ ଯୋଗ୍ୟ ହୋଇପାରନ୍ତି ସେଥିପାଇଁ ଆବେଦନ କରିନାହାନ୍ତି। ଦୟାକରି ସେମାନଙ୍କୁ "
        "ଆବେଦନ କରିବାରେ ସାହାଯ୍ୟ କରନ୍ତୁ; ଆବେଦନ ମାଗଣା।",
        "cols": ("ନାମ", "ଶ୍ରେଣୀ", "ସମ୍ଭାବ୍ୟ ଯୋଜନା"),
        "checks": "ଆବେଦନ ପୂର୍ବରୁ ପ୍ରତ୍ୟେକ ଛାତ୍ରଛାତ୍ରୀଙ୍କର ଯାଞ୍ଚ କରନ୍ତୁ: {checks}।",
        "footer": "ପଙ୍ଖ ତରଫରୁ, ଜନଜାତି ବ୍ୟାପାର ମନ୍ତ୍ରଣାଳୟ ପାଇଁ। ଏହି ତାଲିକା ଗୋପନୀୟ ରଖନ୍ତୁ: ଏହା "
        "କେବଳ ଏହି ଛାତ୍ରଛାତ୍ରୀଙ୍କୁ ଆବେଦନରେ ସାହାଯ୍ୟ ପାଇଁ, ଏବଂ ଲିଙ୍କ 30 ଦିନ ପରେ କାମ କରିବ ନାହିଁ।",
    },
}


# What a school checks before helping a student apply, in a few words each.
_CHECKS = {
    "family_income": {
        "en": "family income",
        "hi": "परिवार की आय",
        "bn": "পরিবারের আয়",
        "gu": "પરિવારની આવક",
        "mr": "कुटुंबाचे उत्पन्न",
        "or": "ପରିବାରର ଆୟ",
    },
    "has_aadhaar_seeded_bank_account": {
        "en": "a bank account linked to Aadhaar",
        "hi": "आधार से जुड़ा बैंक खाता",
        "bn": "আধারের সঙ্গে যুক্ত ব্যাংক অ্যাকাউন্ট",
        "gu": "આધાર સાથે જોડાયેલું બેંક ખાતું",
        "mr": "आधारशी जोडलेले बँक खाते",
        "or": "ଆଧାର ସହ ଯୋଡ଼ା ବ୍ୟାଙ୍କ ଖାତା",
    },
    "holds_other_scholarship": {
        "en": "no other scholarship",
        "hi": "कोई अन्य छात्रवृत्ति नहीं",
        "bn": "অন্য কোনো বৃত্তি নেই",
        "gu": "બીજી કોઈ શિષ્યવૃત્તિ નથી",
        "mr": "दुसरी कोणतीही शिष्यवृत्ती नाही",
        "or": "ଅନ୍ୟ କୌଣସି ଛାତ୍ରବୃତ୍ତି ନାହିଁ",
    },
    "current_mota_award": {
        "en": "no current MoTA scholarship",
        "hi": "अभी कोई जनजातीय कार्य मंत्रालय छात्रवृत्ति नहीं",
        "bn": "এখন জনজাতি বিষয়ক মন্ত্রকের কোনো বৃত্তি নেই",
        "gu": "હાલ આદિજાતિ બાબતોના મંત્રાલયની કોઈ શિષ્યવૃત્તિ નથી",
        "mr": "सध्या आदिवासी कार्य मंत्रालयाची कोणतीही शिष्यवृत्ती नाही",
        "or": "ବର୍ତ୍ତମାନ ଜନଜାତି ବ୍ୟାପାର ମନ୍ତ୍ରଣାଳୟର କୌଣସି ଛାତ୍ରବୃତ୍ତି ନାହିଁ",
    },
    "institution_recognised": {
        "en": "a recognised school",
        "hi": "मान्यता प्राप्त विद्यालय",
        "bn": "স্বীকৃত বিদ্যালয়",
        "gu": "માન્યતા પ્રાપ્ત શાળા",
        "mr": "मान्यताप्राप्त शाळा",
        "or": "ସ୍ୱୀକୃତ ବିଦ୍ୟାଳୟ",
    },
    "school_government_aided_or_local_body": {
        "en": "a government or aided school (for NMMSS)",
        "hi": "सरकारी या सहायता प्राप्त विद्यालय (NMMSS के लिए)",
        "bn": "সরকারি বা সাহায্যপ্রাপ্ত বিদ্যালয় (NMMSS-এর জন্য)",
        "gu": "સરકારી કે અનુદાનિત શાળા (NMMSS માટે)",
        "mr": "सरकारी किंवा अनुदानित शाळा (NMMSS साठी)",
        "or": "ସରକାରୀ ବା ଅନୁଦାନପ୍ରାପ୍ତ ବିଦ୍ୟାଳୟ (NMMSS ପାଇଁ)",
    },
    "selected_in_nmms_exam": {
        "en": "NMMS exam result (for NMMSS)",
        "hi": "NMMS परीक्षा परिणाम (NMMSS के लिए)",
        "bn": "NMMS পরীক্ষার ফল (NMMSS-এর জন্য)",
        "gu": "NMMS પરીક્ષાનું પરિણામ (NMMSS માટે)",
        "mr": "NMMS परीक्षेचा निकाल (NMMSS साठी)",
        "or": "NMMS ପରୀକ୍ଷା ଫଳ (NMMSS ପାଇଁ)",
    },
    "repeating_stage_in_other_subject": {
        "en": "not repeating a class already passed",
        "hi": "पास की हुई कक्षा दोबारा नहीं",
        "bn": "আগে পাস করা শ্রেণি আবার পড়ছে না",
        "gu": "પાસ કરેલું ધોરણ ફરી ભણતા નથી",
        "mr": "उत्तीर्ण झालेली इयत्ता पुन्हा शिकत नाही",
        "or": "ପାସ୍ କରିଥିବା ଶ୍ରେଣୀ ପୁଣି ପଢ଼ୁନାହାନ୍ତି",
    },
    "admitted_to_top_class_institute": {
        "en": "admission to a Top Class institute",
        "hi": "टॉप क्लास संस्थान में प्रवेश",
        "bn": "টপ ক্লাস প্রতিষ্ঠানে ভর্তি",
        "gu": "ટોપ ક્લાસ સંસ્થામાં પ્રવેશ",
        "mr": "टॉप क्लास संस्थेत प्रवेश",
        "or": "ଟପ୍ କ୍ଲାସ ଅନୁଷ୍ଠାନରେ ଭର୍ତ୍ତି",
    },
}


def _checks(rows: list[dict], language: str) -> list[str]:
    names = {f for row in rows for scheme in row["likely_schemes"] for f in scheme["to_confirm"]}
    specs = pankh_rules.fact_specs()
    return [
        _CHECKS[name][language] if name in _CHECKS else specs[name].label
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
