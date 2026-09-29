"""What JAGO can look up or do, each built on the engines, never on the model's own judgement.

Tools return only the fields a reply needs: no identity numbers, no documents, no names.
"""

from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import pankh_rules
from app.academic_year import current_academic_year, label
from app.applications.service import track
from app.config import Settings
from app.documents.reading import KIND_NAMES, Kind
from app.facts.service import FactSource, current_facts, fact_statuses, record_facts
from app.models import Identity, Student, UploadedDocument, VerificationException
from app.renewal.service import plans
from app.sources.http import SourceUnavailable
from app.sources.scholarship_systems import ScholarshipSystemsClient
from pankh_rules.planner import OPPORTUNITIES


@dataclass
class ToolContext:
    session: AsyncSession
    settings: Settings
    http: httpx.AsyncClient
    student: Student
    language: str


def _citation(citation: pankh_rules.Citation) -> dict[str, Any]:
    return {"title": f"{citation.clause}, page {citation.page}", "url": citation.url}


async def my_eligibility(ctx: ToolContext) -> dict[str, Any]:
    facts = await current_facts(ctx.session, ctx.student.id)
    year = current_academic_year()
    results = pankh_rules.evaluate(facts, year)
    return {
        "academic_year": label(year),
        "schemes": [
            {
                "scheme_id": r.scheme.id,
                "scheme": r.scheme.short_name,
                "status": r.status.value,
                "unmet": [
                    {
                        "rule": x.title,
                        "reason": x.reason,
                        "what_to_do": x.remedy,
                        "source": _citation(x.rule.citation),
                    }
                    for x in r.rules
                    if x.outcome is pankh_rules.Outcome.FAIL
                ],
                "answers_needed": len(r.missing_facts),
                "headline_benefit": r.scheme.benefits[0].text if r.scheme.benefits else None,
            }
            for r in results
        ],
        "next_questions": pankh_rules.next_facts(results)[:3],
    }


async def next_question(ctx: ToolContext) -> dict[str, Any]:
    facts = await current_facts(ctx.session, ctx.student.id)
    remaining = pankh_rules.next_facts(pankh_rules.evaluate(facts, current_academic_year()))
    if not remaining:
        return {"done": True}
    spec = pankh_rules.fact_specs()[remaining[0]]
    return {
        "done": False,
        "fact": spec.name,
        "question": spec.question.get(ctx.language, spec.question["en"]),
        "kind": spec.kind.value,
        "choices": [c.labels.get(ctx.language, c.label) for c in spec.choices],
        "remaining": len(remaining),
    }


async def record_answer(ctx: ToolContext, fact: str, value: Any) -> dict[str, Any]:
    try:
        await record_facts(ctx.session, ctx.student.id, {fact: value}, FactSource.SELF_DECLARED)
    except pankh_rules.FactError as error:
        return {"recorded": False, "problem": str(error)}
    return {"recorded": True, "fact": fact}


async def my_applications(ctx: ToolContext) -> dict[str, Any]:
    try:
        tracked = await track(
            ctx.session, ctx.student, ScholarshipSystemsClient(ctx.http, ctx.settings)
        )
    except SourceUnavailable:
        return {"available": False}
    if not tracked.linked:
        return {"linked": False}
    today = date.today()
    return {
        "linked": True,
        "applications": [
            {
                "scheme": pankh_rules.SCHEMES[a.scheme_id].short_name,
                "system": a.source_system,
                "stage": a.stage.value,
                "status": a.status_text,
                "waiting_on": a.waiting_on,
                "days_waiting": a.days_waiting(today),
                "stalled": a.is_stalled(today),
                "deficiency": None
                if a.deficiency is None
                else {"reason": a.deficiency.reason, "fix": a.deficiency.fix},
                "received": a.received,
                "payment_problems": [
                    {
                        "instalment": i.number,
                        "amount": i.amount,
                        "reason": i.problem.reason,
                        "fix": i.problem.fix,
                    }
                    for i in a.instalments
                    if i.problem
                ],
            }
            for a in tracked.applications
        ],
    }


async def my_documents(ctx: ToolContext) -> dict[str, Any]:
    linked = await ctx.session.get(Identity, ctx.student.id) is not None
    issues = (
        await ctx.session.scalars(
            select(VerificationException)
            .where(VerificationException.student_id == ctx.student.id)
            .where(VerificationException.status.in_(("open", "rejected")))
        )
    ).all()
    uploads = (
        await ctx.session.scalars(
            select(UploadedDocument)
            .where(UploadedDocument.student_id == ctx.student.id)
            .where(UploadedDocument.status.not_in(("deleted", "replaced")))
        )
    ).all()
    return {
        "digilocker_linked": linked,
        "uploaded_photos": [
            {"document": KIND_NAMES[Kind(u.kind)], "status": u.status} for u in uploads
        ],
        "issues": [
            {
                "message": e.message,
                "what_to_do": e.remedy,
                "status": e.status,
                "reviewer_note": e.resolution,
            }
            for e in issues
        ],
    }


async def my_renewal(ctx: ToolContext) -> dict[str, Any]:
    try:
        tracked = await track(
            ctx.session, ctx.student, ScholarshipSystemsClient(ctx.http, ctx.settings)
        )
        applications = tracked.applications
    except SourceUnavailable:
        applications = []
    statuses = await fact_statuses(ctx.session, ctx.student.id)
    return {
        "renewals": [
            {
                "scheme": p.scheme,
                "next_year": p.next_year,
                "income_year": f"{int(p.next_year[:4]) - 1}-{int(p.next_year[:4]) % 100:02d}",
                "continuing": p.continuing,
                "apply_fresh_for": p.instead,
                "to_get_ready": [c.id for c in p.checks if not c.done],
                "apply_on": p.apply_on,
                "apply_url": p.apply_url,
            }
            for p in plans(applications, statuses)
        ]
    }


async def scheme_path(ctx: ToolContext, what_if: str | None = None) -> dict[str, Any]:
    """The Scheme Path ahead, and where one achievable condition would unlock a better Scheme."""
    facts = await current_facts(ctx.session, ctx.student.id)
    levels = {
        c.key: c.labels.get(ctx.language, c.label)
        for c in pankh_rules.fact_specs()["education_level"].choices
    }
    stages = pankh_rules.plan_path(facts, current_academic_year())
    if not stages:
        return {"known": False, "missing": "education_level"}
    result: dict[str, Any] = {
        "known": True,
        "stages": [
            {
                "stage": levels.get(s.level, s.level),
                "years": s.label,
                "recommended": s.recommended.scheme if s.recommended else None,
                "value": s.recommended.value.text if s.recommended else None,
                "needs_answers": s.needs_answers,
                "could_unlock": [o.scheme for o in s.opportunities],
            }
            for s in stages
        ],
    }
    if what_if in OPPORTUNITIES:
        hit = next(
            ((s, o) for s in stages for o in s.opportunities if o.scheme_id == what_if),
            None,
        )
        result["what_if"] = (
            {"scheme": pankh_rules.SCHEMES[what_if].short_name, "reachable": False}
            if hit is None
            else {
                "scheme": hit[1].scheme,
                "reachable": True,
                "stage": levels.get(hit[0].level, hit[0].level),
                "years": hit[0].label,
                "condition": hit[1].condition,
                "value": hit[1].value.text,
                "instead_of": hit[0].recommended.scheme if hit[0].recommended else None,
                "source": _citation(hit[1].value.citation),
            }
        )
    return result


async def scheme_details(ctx: ToolContext, scheme_id: str) -> dict[str, Any]:
    scheme = pankh_rules.SCHEMES.get(scheme_id)
    if scheme is None:
        return {"found": False, "schemes": list(pankh_rules.SCHEMES)}
    return {
        "found": True,
        "scheme": scheme.name,
        "summary": scheme.summary,
        "benefits": [{"text": b.text, "source": _citation(b.citation)} for b in scheme.benefits],
        "apply_on": scheme.system_of_record,
        "apply_url": scheme.apply_url,
        "when": scheme.application_window,
    }


TOOLS = {
    "my_eligibility": (
        my_eligibility,
        "Which Schemes the Student qualifies for, why not, and what to do.",
        {},
    ),
    "next_question": (next_question, "The most useful question to ask the Student next.", {}),
    "record_answer": (
        record_answer,
        "Save the Student's answer to a question about themselves.",
        {
            "fact": {"type": "string", "enum": list(pankh_rules.fact_specs())},
            "value": {"description": "true/false, a number, a YYYY-MM-DD date, or a choice key"},
        },
    ),
    "my_applications": (
        my_applications,
        "The Student's applications and payments, with any problem and its fix.",
        {},
    ),
    "my_documents": (my_documents, "Problems found with the Student's documents, and the fix.", {}),
    "my_renewal": (
        my_renewal,
        "Next year's application for each Scheme the Student holds, and what to get ready.",
        {},
    ),
    "scheme_path": (
        scheme_path,
        "Which Scheme to hold at each stage ahead. With what_if, whether an achievable condition "
        "(top_class: a Top Class institute; nfst: NET; nos: study abroad; csss: top 20% in Class "
        "XII; pragati: AICTE technical degree) would unlock a better Scheme, and when.",
        {
            "what_if": {
                "type": "string",
                "enum": list(OPPORTUNITIES),
                "optional": True,
            }
        },
    ),
    "scheme_details": (
        scheme_details,
        "Benefits, how and when to apply for one Scheme.",
        {"scheme_id": {"type": "string", "enum": list(pankh_rules.SCHEMES)}},
    ),
}


def tool_schemas() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        name: {k: v for k, v in spec.items() if k != "optional"}
                        for name, spec in params.items()
                    },
                    "required": [name for name, spec in params.items() if not spec.get("optional")],
                },
            },
        }
        for name, (_, description, params) in TOOLS.items()
    ]


async def call_tool(ctx: ToolContext, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if name not in TOOLS:
        return {"error": f"No tool called {name}"}
    handler = TOOLS[name][0]
    try:
        return await handler(ctx, **arguments)
    except TypeError as error:
        return {"error": f"Wrong arguments for {name}: {error}"}
