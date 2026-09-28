"""Reading issuer certificates and turning them into Facts.

DigiLocker issuers publish certificates as XML with a common envelope (issuer, holder) and a
document-specific CertificateData element. Only Facts are kept from a certificate; the
certificate itself is never stored.
"""

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

# DigiLocker document types Pankh reads.
AADHAAR = "ADHAR"
CASTE = "CSCER"
INCOME = "INCER"
CLASS_X = "SSCER"
NET_SCORECARD = "NETSC"
DISABILITY = "UDIDC"


class CertificateError(ValueError):
    pass


@dataclass(frozen=True)
class Certificate:
    doctype: str
    number: str
    issuer: str
    issue_date: date | None
    holder_name: str
    holder_dob: date | None
    holder_gender: str | None
    holder_district: str | None = None
    holder_state: str | None = None
    data: dict[str, str] = field(default_factory=dict)


def parse_certificate(xml: str) -> Certificate:
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as error:
        raise CertificateError(f"Not a readable certificate: {error}") from error
    person = root.find("IssuedTo/Person")
    if root.tag != "Certificate" or person is None:
        raise CertificateError("Not an issuer certificate")
    organisation = root.find("IssuedBy/Organization")
    address = person.find("Address")
    data_element = root.find("CertificateData")
    data = {}
    if data_element is not None and len(data_element):
        data = dict(data_element[0].attrib)
    return Certificate(
        doctype=root.get("type", ""),
        number=root.get("number", ""),
        issuer=organisation.get("name", "") if organisation is not None else "",
        issue_date=_date(root.get("issueDate")),
        holder_name=person.get("name", ""),
        holder_dob=_date(person.get("dob")),
        holder_gender=person.get("gender"),
        holder_district=address.get("district") if address is not None else None,
        holder_state=address.get("state") if address is not None else None,
        data=data,
    )


@dataclass(frozen=True)
class CertificateFacts:
    facts: dict[str, Any]
    stale_reason: str | None = None
    """Set when the certificate is too old to prove its Facts for this academic year."""


def facts_from_certificate(certificate: Certificate, academic_year: int) -> CertificateFacts:
    """The Facts a certificate proves, for Rules in the given academic year."""
    data = certificate.data
    match certificate.doctype:
        case "ADHAR" | "SSCER":
            facts = {"date_of_birth": certificate.holder_dob} if certificate.holder_dob else {}
            return CertificateFacts(facts)
        case "CSCER":
            return CertificateFacts({"is_scheduled_tribe": data.get("category") == "ST"})
        case "INCER":
            amount = float(data["annualIncome"])
            # Guidelines ask for the financial year immediately before the academic year.
            expected = f"{academic_year - 1}-{academic_year % 100:02d}"
            year = data.get("financialYear", "")
            stale = None
            if year != expected:
                stale = (
                    f"The income certificate is for {year or 'an unknown year'}; "
                    f"{academic_year}-{(academic_year + 1) % 100:02d} needs one for {expected}."
                )
            return CertificateFacts({"family_income": amount}, stale)
        case "NETSC":
            return CertificateFacts({"net_jrf_qualified": data.get("category") in ("JRF", "NET")})
        case _:
            return CertificateFacts({})


def _date(value: str | None) -> date | None:
    if not value:
        return None
    for layout in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, layout).date()
        except ValueError:
            continue
    return None
