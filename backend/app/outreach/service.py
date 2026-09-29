"""The outreach agent: tells schools and families about Unreached Students' scholarships.

It drafts every message from fixed templates and the rules engine's likely Schemes, shows them
to an official, and sends only after that official approves. Contacts are looked up in UDISE+ at
the moment of sending and never stored.
"""

import base64
import hashlib
import hmac
import uuid
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.sms import SmsSender
from app.config import Settings
from app.models import Campaign, CampaignTarget, CoverageRun, OutreachLink
from app.outreach.messages import family_message, school_message
from app.sources.http import SourceUnavailable
from app.sources.registers import RegistersClient

LIST_TTL = timedelta(days=30)
# A student is not messaged again on the same channel within this time.
QUIET_PERIOD = timedelta(days=30)


@dataclass(frozen=True)
class Message:
    to: str  # "school" or "family"
    about: list[str]  # student refs
    text: str
    school: str | None = None


def unreached_rows(
    run: CoverageRun, state: str, district: str | None, udise_code: str | None = None
) -> list[dict[str, Any]]:
    return [
        row
        for row in run.unreached
        if row["state"] == state
        and (district is None or row["district"] == district)
        and (udise_code is None or row["udise_code"] == udise_code)
    ]


async def recently_messaged(session: AsyncSession, channel: str) -> set[str]:
    since = datetime.now(UTC) - QUIET_PERIOD
    rows = await session.scalars(
        select(CampaignTarget.student_ref)
        .join(Campaign, Campaign.id == CampaignTarget.campaign_id)
        .where(Campaign.channel == channel)
        .where(Campaign.status == "sent")
        .where(Campaign.sent_at >= since)
        .where(CampaignTarget.status == "sent")
    )
    return set(rows.all())


def link_code(settings: Settings, campaign_id: uuid.UUID, udise_code: str) -> str:
    """The same short code every time for a campaign and school, unguessable without the key."""
    digest = hmac.new(
        settings.secret_key.encode(), f"{campaign_id}:{udise_code}".encode(), hashlib.sha256
    ).digest()
    return base64.b32encode(digest[:10]).decode().lower()


async def list_link(
    session: AsyncSession, settings: Settings, campaign_id: uuid.UUID, udise_code: str
) -> str:
    code = link_code(settings, campaign_id, udise_code)
    await session.execute(
        insert(OutreachLink)
        .values(code=code, campaign_id=campaign_id, udise_code=udise_code)
        .on_conflict_do_nothing()
    )
    return f"{settings.public_api_url.rstrip('/')}/v1/outreach/l/{code}"


def _schemes(rows: list[dict[str, Any]]) -> list[str]:
    return [scheme["scheme"] for row in rows for scheme in row["likely_schemes"]]


async def messages(
    session: AsyncSession,
    campaign: Campaign,
    rows: list[dict[str, Any]],
    registers: RegistersClient,
    settings: Settings,
    limit: int | None = None,
) -> list[Message]:
    """The messages the campaign sends, in the campaign's language. Contacts are not included."""
    language = campaign.language  # type: ignore[assignment]
    drafted: list[Message] = []
    if campaign.channel == "school":
        by_school: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            by_school[row["udise_code"]].append(row)
        for code, students in list(by_school.items())[:limit]:
            school = await registers.udise_school(code)
            name = school["name"] if school else code
            text = school_message(
                language,
                name,
                len(students),
                _schemes(students),
                await list_link(session, settings, campaign.id, code),
            )
            drafted.append(Message("school", [s["student_ref"] for s in students], text, name))
    else:
        for row in rows[:limit]:
            text = family_message(language, row["name"], _schemes([row]))
            drafted.append(Message("family", [row["student_ref"]], text))
    return drafted


async def send(
    session: AsyncSession,
    campaign: Campaign,
    run: CoverageRun,
    registers: RegistersClient,
    sms: SmsSender,
    settings: Settings,
) -> dict[str, int]:
    targets = {
        t.student_ref: t
        for t in (
            await session.scalars(
                select(CampaignTarget).where(CampaignTarget.campaign_id == campaign.id)
            )
        ).all()
    }
    rows = [row for row in run.unreached if row["student_ref"] in targets]
    now = datetime.now(UTC)
    for message in await messages(session, campaign, rows, registers, settings):
        try:
            if message.to == "school":
                school = await registers.udise_school(targets[message.about[0]].udise_code)
                phone = ((school or {}).get("nodal_officer") or {}).get("phone")
            else:
                contact = await registers.udise_student_contact(message.about[0])
                phone = (contact or {}).get("guardian_phone")
        except SourceUnavailable:
            for ref in message.about:
                targets[ref].status = "failed"
            continue
        if not phone:
            for ref in message.about:
                targets[ref].status = "no_contact"
            continue
        await sms.send_text(phone, message.text)
        for ref in message.about:
            targets[ref].status = "sent"
            targets[ref].sent_at = now
    counts: dict[str, int] = defaultdict(int)
    for target in targets.values():
        counts[target.status] += 1
    return dict(counts)
