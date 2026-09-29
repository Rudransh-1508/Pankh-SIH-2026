"""Paper certificates a synthetic person holds, printed as a page to photograph.

For trying the document agent end to end: open a page, photograph it with the Pankh app, and the
app reads it as it would a real certificate. People whose certificate was issued through
e-District get one the register can verify; the rest get an older paper certificate it cannot.
"""

import hashlib
from datetime import date
from html import escape
from typing import Literal

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import HTMLResponse

from pankh_simulators.population import Person, population
from pankh_simulators.registers import certificate_number

router = APIRouter(prefix="/paper", tags=["paper certificates"])

_PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<style>
  body {{ margin: 0; background: #e9e4d8; font-family: Georgia, 'Noto Serif', serif; }}
  .sheet {{ max-width: 640px; margin: 24px auto; background: #fffdf6; padding: 40px 44px;
    border: 3px double #6b5b3e; color: #1d1a14; line-height: 1.7; }}
  .gov {{ text-align: center; font-weight: bold; letter-spacing: .04em; }}
  h1 {{ text-align: center; font-size: 22px; text-decoration: underline; margin: 18px 0 4px; }}
  .sub {{ text-align: center; margin: 0 0 20px; }}
  .meta {{ display: flex; justify-content: space-between; margin-bottom: 18px; }}
  .sign {{ margin-top: 48px; text-align: right; }}
</style></head>
<body><div class="sheet">{body}</div></body></html>"""


def _paper_number(person: Person, doctype: str) -> str:
    """A number for a certificate issued on paper before e-District, which no register holds."""
    digest = hashlib.sha256(f"{person.id}:{doctype}:paper".encode()).hexdigest()
    return f"{person.state.code}/{doctype[:2]}/{int(digest[:6], 16) % 90000 + 10000}/2012"


def _caste(person: Person) -> str:
    if person.tribe is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This person holds no ST certificate")
    if person.has_caste_certificate:
        number, issued = certificate_number(person, "CSCER"), date(2019, 3, 4)
    else:
        number, issued = _paper_number(person, "CSCER"), date(2012, 8, 21)
    title = "Mr" if person.gender == "M" else "Kumari"
    relation = "Son" if person.gender == "M" else "Daughter"
    return f"""
<div class="gov">GOVERNMENT OF {escape(person.state.name.upper())}</div>
<div class="gov">Office of the Sub-Divisional Officer, {escape(person.district)}</div>
<h1>CASTE CERTIFICATE</h1><p class="sub">(For Scheduled Tribes)</p>
<div class="meta"><span>Certificate No. : {number}</span>
<span>Date : {issued:%d/%m/%Y}</span></div>
<p>This is to certify that {title} {escape(person.caste_certificate_spelling)}, {relation} of
Shri {escape(person.surname)}, resident of District {escape(person.district)} in the State of
{escape(person.state.name)}, belongs to the {escape(person.tribe.name)} community, which is
recognised as a Scheduled Tribe under the Constitution (Scheduled Tribes) Order, 1950.</p>
<p class="sign">Sub-Divisional Officer<br>{escape(person.district)}</p>"""


def _income(person: Person) -> str:
    amount, financial_year, issued = person.income_certificate()
    number = (
        certificate_number(person, "INCER")
        if person.has_income_certificate
        else _paper_number(person, "INCER")
    )
    title = "Shri" if person.gender == "M" else "Kumari"
    return f"""
<div class="gov">GOVERNMENT OF {escape(person.state.name.upper())}</div>
<div class="gov">Office of the Tehsildar, {escape(person.district)}</div>
<h1>INCOME CERTIFICATE</h1><p class="sub">&nbsp;</p>
<div class="meta"><span>Certificate No. : {number}</span>
<span>Date : {issued:%d/%m/%Y}</span></div>
<p>This is to certify that {title} {escape(person.name)}, resident of District
{escape(person.district)}, {escape(person.state.name)}, has an annual income from all sources of
Rs. {amount:,}/- for the financial year {financial_year}, as the income of the family.</p>
<p class="sign">Tehsildar<br>{escape(person.district)}</p>"""


@router.get("/{phone}/{kind}", response_class=HTMLResponse)
async def paper_certificate(phone: str, kind: Literal["caste", "income"]) -> str:
    person = population().by_phone(phone)
    if person is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No synthetic person has that phone")
    body = _caste(person) if kind == "caste" else _income(person)
    return _PAGE.format(title=f"{kind.title()} certificate", body=body)
