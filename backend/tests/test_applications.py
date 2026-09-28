from datetime import date

from pankh_simulators.population import population
from pankh_simulators.scholarship_systems import nsp_applications

from app.applications.tracker import Stage, exclusivity_warning, from_nsp
from app.sources.http import SourceUnavailable
from app.sources.scholarship_systems import ScholarshipSystemsClient


def _person(condition):
    return next(p for p in population().people if condition(p))


async def test_needs_digilocker_to_find_applications(client, auth):
    body = (await client.get("/v1/me/applications", headers=auth)).json()
    assert body == {"linked": False, "stale_sources": [], "warning": None, "applications": []}


async def test_tracks_nsp_applications_and_traces_payments(client, auth, link_digilocker):
    person = _person(
        lambda p: p.mota_award == "post_matric" and any(a["payments"] for a in nsp_applications(p))
    )
    await link_digilocker(auth, person)
    body = (await client.get("/v1/me/applications", headers=auth)).json()
    (application,) = body["applications"]
    assert application["source_system"] == "NSP"
    assert application["scheme_name"] == "Post-Matric Scholarship for ST Students"
    assert application["instalments"]
    for instalment in application["instalments"]:
        if instalment["status"] == "failed":
            assert instalment["problem"]["fix"]


async def test_nfst_fellows_come_from_sfmp(client, auth, link_digilocker):
    person = _person(lambda p: p.mota_award == "nfst" and p.has_scholarship_record)
    await link_digilocker(auth, person)
    body = (await client.get("/v1/me/applications", headers=auth)).json()
    assert body["applications"][0]["source_system"] == "SFMP"
    assert body["applications"][0]["scheme_id"] == "nfst"


async def test_shows_last_seen_applications_when_a_system_is_down(
    client, auth, link_digilocker, monkeypatch
):
    person = _person(lambda p: p.mota_award == "post_matric" and p.has_scholarship_record)
    await link_digilocker(auth, person)
    first = (await client.get("/v1/me/applications", headers=auth)).json()

    async def down(self, reference_key):
        raise SourceUnavailable("NSP is down")

    monkeypatch.setattr(ScholarshipSystemsClient, "nsp_applications", down)
    body = (await client.get("/v1/me/applications", headers=auth)).json()
    assert body["stale_sources"] == ["NSP"]
    assert body["applications"][0]["external_id"] == first["applications"][0]["external_id"]


def _nsp(status: str, days_ago: int, remark: str | None = None) -> dict:
    on = date.fromordinal(date.today().toordinal() - days_ago).isoformat()
    return {
        "application_id": "NSP1",
        "scheme_code": "POST-MATRIC-ST",
        "academic_year": "2026-27",
        "status": status,
        "defect_remarks": remark,
        "history": [{"status": status, "on": on}],
        "sanctioned_amount": None,
        "payments": [],
    }


def test_nsp_stages_map_to_who_is_being_waited_on():
    application = from_nsp(_nsp("Verified by Institute", 10))
    assert (application.stage, application.waiting_on) == (Stage.UNDER_VERIFICATION, "district")
    assert not application.is_stalled(date.today())
    assert from_nsp(_nsp("Verified by Institute", 45)).is_stalled(date.today())


def test_defective_applications_become_deficiencies_for_the_student():
    application = from_nsp(
        _nsp("Defective at Institute", 3, "Bonafide certificate missing institute seal.")
    )
    assert application.waiting_on == "you"
    assert "Bonafide certificate missing institute seal." in application.deficiency.reason
    assert "resubmit" in application.deficiency.fix


def test_two_active_mota_schemes_are_flagged():
    post_matric = from_nsp(_nsp("Submitted", 5))
    top_class = from_nsp(_nsp("Submitted", 5) | {"scheme_code": "TOPCLASS-ST"})
    assert exclusivity_warning([post_matric, top_class])
    assert exclusivity_warning([post_matric]) is None
