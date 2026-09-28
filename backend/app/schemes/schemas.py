from typing import Literal

from pydantic import BaseModel

import pankh_rules


class CitationOut(BaseModel):
    source_id: str
    source_title: str
    page: int
    clause: str
    url: str

    @classmethod
    def of(cls, citation: pankh_rules.Citation) -> "CitationOut":
        return cls(
            source_id=citation.source_id,
            source_title=citation.source.title,
            page=citation.page,
            clause=citation.clause,
            url=citation.url,
        )


class BenefitOut(BaseModel):
    text: str
    citation: CitationOut


class SchemeOut(BaseModel):
    id: str
    name: str
    short_name: str
    summary: str
    system_of_record: str
    apply_url: str
    application_window: str | None
    benefits: list[BenefitOut]

    @classmethod
    def of(cls, scheme: pankh_rules.Scheme) -> "SchemeOut":
        return cls(
            id=scheme.id,
            name=scheme.name,
            short_name=scheme.short_name,
            summary=scheme.summary,
            system_of_record=scheme.system_of_record,
            apply_url=scheme.apply_url,
            application_window=scheme.application_window,
            benefits=[
                BenefitOut(text=b.text, citation=CitationOut.of(b.citation))
                for b in scheme.benefits
            ],
        )


class ChoiceOut(BaseModel):
    key: str
    label: str
    labels: dict[str, str]


class FactSpecOut(BaseModel):
    name: str
    label: str
    description: str | None
    kind: Literal["boolean", "number", "date", "choice"]
    question: dict[str, str]
    help: dict[str, str] | None
    choices: list[ChoiceOut]

    @classmethod
    def of(cls, spec: pankh_rules.FactSpec) -> "FactSpecOut":
        return cls(
            name=spec.name,
            label=spec.label,
            description=spec.description,
            kind=spec.kind.value,
            question=dict(spec.question),
            help=dict(spec.help) if spec.help else None,
            choices=[
                ChoiceOut(key=c.key, label=c.label, labels=dict(c.labels)) for c in spec.choices
            ],
        )


class SourceOut(BaseModel):
    id: str
    title: str
    url: str
    sha256: str
    pages: int
    issued: str | None
    effective: str | None


class InstituteOut(BaseModel):
    id: int
    name: str
    location: str
    state: str
    courses: str
    citation: CitationOut


class RuleResultOut(BaseModel):
    id: str
    title: str
    outcome: Literal["pass", "fail", "waived", "unknown"]
    reason: str | None
    remedy: str | None
    missing_facts: list[str]
    citation: CitationOut


class SchemeResultOut(BaseModel):
    scheme: SchemeOut
    status: Literal["eligible", "not_eligible", "needs_information"]
    rules: list[RuleResultOut]
    missing_facts: list[str]

    @classmethod
    def of(cls, result: pankh_rules.SchemeResult) -> "SchemeResultOut":
        return cls(
            scheme=SchemeOut.of(result.scheme),
            status=result.status.value,
            missing_facts=list(result.missing_facts),
            rules=[
                RuleResultOut(
                    id=r.rule.id,
                    title=r.title,
                    outcome=r.outcome.value,
                    reason=r.reason,
                    remedy=r.remedy,
                    missing_facts=list(r.missing_facts),
                    citation=CitationOut.of(r.rule.citation),
                )
                for r in result.rules
            ],
        )


class EligibilityOut(BaseModel):
    academic_year: int
    academic_year_label: str
    schemes: list[SchemeResultOut]
    next_facts: list[str]
