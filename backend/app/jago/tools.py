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
from app.facts.service import FactSource, current_facts, record_facts
from app.models import Identity, Student, VerificationException
from app.sources.http import SourceUnavailable
from app.sources.scholarship_systems import ScholarshipSystemsClient


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
    return {
        "digilocker_linked": linked,
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
                "parameters": {"type": "object", "properties": params, "required": list(params)},
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
