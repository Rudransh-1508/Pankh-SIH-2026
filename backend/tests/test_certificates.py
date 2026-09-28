from datetime import date

import pytest

from app.verification.certificates import (
    CertificateError,
    facts_from_certificate,
    parse_certificate,
)

INCOME = """<?xml version="1.0"?>
<Certificate type="INCER" number="AB12" issueDate="20-04-2026" status="A">
  <IssuedBy><Organization name="e-District, Jharkhand"/></IssuedBy>
  <IssuedTo><Person name="Sunita Murmu" dob="14-03-2006" gender="F"/></IssuedTo>
  <CertificateData><Income annualIncome="180000" financialYear="2025-26"/></CertificateData>
</Certificate>"""


def test_parses_the_issuer_envelope():
    certificate = parse_certificate(INCOME)
    assert certificate.holder_name == "Sunita Murmu"
    assert certificate.holder_dob == date(2006, 3, 14)
    assert certificate.data["annualIncome"] == "180000"


def test_income_must_be_for_the_year_before_the_session():
    certificate = parse_certificate(INCOME)
    assert facts_from_certificate(certificate, 2026).stale_reason is None
    assert facts_from_certificate(certificate, 2026).facts == {"family_income": 180000.0}
    stale = facts_from_certificate(certificate, 2027)
    assert "2026-27" in stale.stale_reason


def test_rejects_what_is_not_a_certificate():
    with pytest.raises(CertificateError):
        parse_certificate("<html/>")
    with pytest.raises(CertificateError):
        parse_certificate("not xml")
