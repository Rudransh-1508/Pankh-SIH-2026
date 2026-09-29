"""JAGO: one conversation through which a Student reaches everything Pankh can do.

With a language model configured, the model understands the Student and chooses tools. Without
one, JAGO's own understanding answers the common questions and asks intake questions. Either
way every fact in a reply comes from a tool, built on the engines and the Student's records.
"""

import json
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import select

from app.jago import tools
from app.jago.llm import ChatModel, ModelUnavailable
from app.jago.texts import LANGUAGE_NAMES, SYSTEM_PROMPT, TEXT, WHO
from app.jago.tools import ToolContext
from app.jago.understanding import classify, parse_answer
from app.models import JagoMessage

MAX_TOOL_ROUNDS = 6
HISTORY_TURNS = 12


@dataclass
class Reply:
    text: str
    sources: list[dict[str, str]] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    asking: str | None = None
    """The Fact JAGO just asked about, so the next message can be read as its answer."""
    trace: list[dict[str, Any]] = field(default_factory=list)


def _linked_sources(value: Any, found: list[dict[str, str]]) -> None:
    """Collect every cited source in a tool result, for the reply's source list."""
    if isinstance(value, dict):
        if set(value) >= {"title", "url"} and value not in found:
            found.append({"title": value["title"], "url": value["url"]})
        for item in value.values():
            _linked_sources(item, found)
    elif isinstance(value, list):
        for item in value:
            _linked_sources(item, found)


class Jago:
    def __init__(self, ctx: ToolContext, model: ChatModel | None) -> None:
        self.ctx = ctx
        self.model = model
        self.text = TEXT.get(ctx.language, TEXT["en"])

    async def reply(self, message: str) -> Reply:
        history = await self._history()
        if self.model is not None:
            try:
                reply = await self._with_model(message, history)
            except ModelUnavailable:
                reply = await self._grounded(message, history)
        else:
            reply = await self._grounded(message, history)
        self._remember(message, reply)
        await self.ctx.session.flush()
        return reply

    async def _history(self) -> list[JagoMessage]:
        rows = (
            await self.ctx.session.scalars(
                select(JagoMessage)
                .where(JagoMessage.student_id == self.ctx.student.id)
                .order_by(JagoMessage.created_at.desc(), JagoMessage.id.desc())
                .limit(HISTORY_TURNS)
            )
        ).all()
        return list(reversed(rows))

    def _remember(self, message: str, reply: Reply) -> None:
        student = self.ctx.student.id
        language = self.ctx.language
        self.ctx.session.add(
            JagoMessage(
                student_id=student, role="user", content=message, language=language, meta={}
            )
        )
        self.ctx.session.add(
            JagoMessage(
                student_id=student,
                role="assistant",
                content=reply.text,
                language=language,
                meta={
                    "asking": reply.asking,
                    "sources": reply.sources,
                    "trace": reply.trace,
                    "suggestions": reply.suggestions,
                },
            )
        )

    async def _tool(self, reply: Reply, name: str, **arguments: Any) -> dict[str, Any]:
        result = await tools.call_tool(self.ctx, name, arguments)
        reply.trace.append({"tool": name, "arguments": arguments})
        _linked_sources(result, reply.sources)
        return result

    # Without a model

    async def _grounded(self, message: str, history: list[JagoMessage]) -> Reply:
        reply = Reply(text="", suggestions=self.text["suggest"])
        pending = (
            history[-1].meta.get("asking") if history and history[-1].role == "assistant" else None
        )
        if pending:
            value = parse_answer(pending, message)
            if value is not None:
                await self._tool(reply, "record_answer", fact=pending, value=value)
                return await self._ask_next(reply, prefix=self.text["saved"])
            if classify(message) == "unknown":
                question = await self._tool(reply, "next_question")
                reply.text = self.text["not_understood"].format(
                    question=question.get("question", "")
                )
                reply.asking = question.get("fact")
                return reply
        intent = classify(message)
        if intent.startswith("scheme:"):
            return await self._scheme(reply, intent.split(":", 1)[1])
        handler = {
            "eligibility": self._eligibility,
            "applications": self._applications,
            "payments": self._payments,
            "documents": self._documents,
            "renewal": self._renewal,
            "greeting": self._hello,
        }.get(intent, self._unknown)
        return await handler(reply)

    async def _ask_next(self, reply: Reply, prefix: str = "") -> Reply:
        question = await self._tool(reply, "next_question")
        if question.get("done"):
            summary = await self._eligibility(Reply(text=""), ask=False)
            reply.text = " ".join(filter(None, [prefix, self.text["all_answered"], summary.text]))
            reply.sources = summary.sources
            return reply
        reply.text = " ".join(filter(None, [prefix, question["question"]]))
        reply.asking = question["fact"]
        reply.suggestions = self._answer_suggestions(question)
        return reply

    def _answer_suggestions(self, question: dict[str, Any]) -> list[str]:
        """Tappable answers: the choices, or yes and no. Numbers and dates are typed."""
        if question["kind"] == "boolean":
            return ["Yes", "No"] if self.ctx.language == "en" else ["हाँ", "नहीं"]
        return question["choices"][:6]

    async def _eligibility(self, reply: Reply, ask: bool = True) -> Reply:
        result = await self._tool(reply, "my_eligibility")
        eligible = [s["scheme"] for s in result["schemes"] if s["status"] == "eligible"]
        undecided = [s for s in result["schemes"] if s["status"] == "needs_information"]
        parts = [self.text["eligible"].format(schemes=", ".join(eligible))] if eligible else []
        if not eligible and not undecided:
            parts.append(self.text["none_eligible"])
            for scheme in result["schemes"][:1]:
                for unmet in scheme["unmet"][:1]:
                    parts.append(f"{scheme['scheme']}: {unmet['reason']}")
        if undecided and ask:
            question = await self._tool(reply, "next_question")
            if not question.get("done"):
                singular, plural = self.text["scheme_word"]
                parts.append(
                    self.text["needs"].format(
                        count=len(undecided),
                        plural=singular if len(undecided) == 1 else plural,
                        question=question["question"],
                    )
                )
                reply.asking = question["fact"]
                reply.suggestions = self._answer_suggestions(question)
        reply.text = " ".join(parts)
        return reply

    async def _applications(self, reply: Reply) -> Reply:
        result = await self._tool(reply, "my_applications")
        if result.get("available") is False:
            reply.text = self.text["unavailable"]
        elif not result.get("linked"):
            reply.text = self.text["not_linked"]
        elif not result["applications"]:
            reply.text = self.text["no_applications"]
        else:
            lines = []
            for app in result["applications"]:
                who = app["waiting_on"]
                if who and who != "you" and app["days_waiting"] is not None:
                    line = self.text["waiting"].format(
                        scheme=app["scheme"],
                        system=app["system"],
                        who=WHO[self.ctx.language if self.ctx.language in WHO else "en"].get(
                            who, who
                        ),
                        days=app["days_waiting"],
                    )
                    if app["stalled"]:
                        line += self.text["stalled"]
                else:
                    line = self.text["status"].format(
                        scheme=app["scheme"], system=app["system"], status=app["status"]
                    )
                if app["deficiency"]:
                    line += (
                        " "
                        + app["deficiency"]["reason"]
                        + " "
                        + self.text["fix"].format(fix=app["deficiency"]["fix"])
                    )
                lines.append(line)
            reply.text = "\n".join(lines)
        return reply

    async def _payments(self, reply: Reply) -> Reply:
        result = await self._tool(reply, "my_applications")
        if result.get("available") is False or not result.get("linked"):
            reply.text = self.text[
                "unavailable" if result.get("available") is False else "not_linked"
            ]
            return reply
        lines = []
        for app in result["applications"]:
            for problem in app["payment_problems"]:
                lines.append(
                    self.text["payment_problem"].format(
                        scheme=app["scheme"],
                        number=problem["instalment"],
                        reason=problem["reason"],
                        fix=problem["fix"],
                    )
                )
            if app["received"]:
                lines.append(
                    self.text["received"].format(
                        scheme=app["scheme"], amount=f"{app['received']:,}"
                    )
                )
            elif not app["payment_problems"]:
                lines.append(self.text["no_money_yet"].format(scheme=app["scheme"]))
        reply.text = "\n".join(lines) or self.text["no_applications"]
        return reply

    async def _documents(self, reply: Reply) -> Reply:
        result = await self._tool(reply, "my_documents")
        if not result["digilocker_linked"]:
            reply.text = self.text["documents_not_linked"]
        elif not result["issues"]:
            reply.text = self.text["documents_ok"]
        else:
            lines = []
            for issue in result["issues"]:
                line = issue["message"]
                if issue["reviewer_note"]:
                    line += " " + self.text["reviewer_note"].format(note=issue["reviewer_note"])
                elif issue["what_to_do"]:
                    line += " " + issue["what_to_do"]
                lines.append(line)
            reply.text = "\n".join(lines)
        return reply

    async def _renewal(self, reply: Reply) -> Reply:
        result = await self._tool(reply, "my_renewal")
        if not result["renewals"]:
            reply.text = self.text["renewal_none"]
            return reply
        checks = self.text["renewal_checks"]
        lines = []
        for plan in result["renewals"]:
            todo = ", ".join(
                checks[c].format(income_year=plan["income_year"]) for c in plan["to_get_ready"]
            )
            template = "renewal_continue" if plan["continuing"] else "renewal_new"
            lines.append(
                self.text[template].format(
                    scheme=plan["scheme"],
                    year=plan["next_year"],
                    instead=plan["apply_fresh_for"] or "",
                    todo=todo,
                    apply_on=plan["apply_on"],
                )
            )
        reply.text = "\n".join(lines)
        return reply

    async def _scheme(self, reply: Reply, scheme_id: str) -> Reply:
        result = await self._tool(reply, "scheme_details", scheme_id=scheme_id)
        benefits = "; ".join(b["text"] for b in result["benefits"][:2])
        reply.text = self.text["scheme"].format(
            name=result["scheme"],
            summary=result["summary"],
            benefits=benefits,
            apply_on=result["apply_on"],
        )
        if result["when"]:
            reply.text += self.text["when"].format(when=result["when"])
        return reply

    async def _hello(self, reply: Reply) -> Reply:
        reply.text = self.text["hello"]
        return reply

    async def _unknown(self, reply: Reply) -> Reply:
        reply.text = self.text["unknown"]
        return reply

    # With a model

    async def _with_model(self, message: str, history: list[JagoMessage]) -> Reply:
        assert self.model is not None
        reply = Reply(text="", suggestions=self.text["suggest"])
        language = LANGUAGE_NAMES.get(self.ctx.language, "English")
        messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT.format(language=language)}
        ]
        messages += [{"role": m.role, "content": m.content} for m in history]
        messages.append({"role": "user", "content": message})
        schemas = tools.tool_schemas()
        for _ in range(MAX_TOOL_ROUNDS):
            turn = await self.model.respond(messages, schemas)
            if not turn.tool_calls:
                reply.text = (turn.text or "").strip() or self.text["unknown"]
                return reply
            messages.append(
                {
                    "role": "assistant",
                    "content": turn.text,
                    "tool_calls": [
                        {
                            "id": c.id,
                            "type": "function",
                            "function": {"name": c.name, "arguments": json.dumps(c.arguments)},
                        }
                        for c in turn.tool_calls
                    ],
                }
            )
            for call in turn.tool_calls:
                result = await self._tool(reply, call.name, **call.arguments)
                if call.name == "next_question" and not result.get("done"):
                    reply.asking = result.get("fact")
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.id,
                        "content": json.dumps(result, default=str),
                    }
                )
        reply.text = self.text["unknown"]
        return reply
