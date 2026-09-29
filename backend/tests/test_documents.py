import html
import re
import uuid
from datetime import UTC, datetime, timedelta

import boto3
import pytest
from httpx import ASGITransport, AsyncClient
from moto import mock_aws
from pankh_simulators.population import population
from sqlalchemy import select

from app.config import get_settings
from app.db import get_sessionmaker
from app.documents import crypto
from app.documents.agent import purge_expired
from app.documents.reading import Kind, read_document
from app.documents.router import get_object_store
from app.documents.storage import FileStore, ObjectNotFound, S3Store
from app.main import app
from app.models import AuditEvent, UploadedDocument
from app.verification.names import match_names

JPEG = b"\xff\xd8\xff\xe0" + b"\x00\x10JFIF" + bytes(range(256)) * 4


@pytest.fixture
def store(tmp_path):
    files = FileStore(tmp_path / "objects")
    app.dependency_overrides[get_object_store] = lambda: files
    yield files
    app.dependency_overrides.pop(get_object_store, None)


async def paper_text(phone: str, kind: str) -> str:
    """The text of a simulator paper certificate, as the phone's OCR would read it."""
    from pankh_simulators.app import app as simulator_app

    async with AsyncClient(
        transport=ASGITransport(app=simulator_app), base_url="http://sim"
    ) as sim:
        page = await sim.get(f"/paper/{phone}/{kind}")
    assert page.status_code == 200, page.text
    body = page.text.split("<body>", 1)[1]
    return html.unescape(re.sub(r"<[^>]+>", "\n", body))


def person_where(**wanted):
    for person in population().people:
        if (
            all(
                (value(getattr(person, key)) if callable(value) else getattr(person, key) == value)
                for key, value in wanted.items()
            )
            and match_names(person.caste_certificate_spelling, person.name).is_match
        ):
            return person
    raise LookupError(wanted)


async def upload(client, auth, kind: str, text: str, data: bytes = JPEG, content_type="image/jpeg"):
    return await client.post(
        "/v1/me/documents/uploads",
        headers=auth,
        data={"kind": kind, "text": text},
        files={"file": ("photo.jpg", data, content_type)},
    )


# Reading


def test_reads_an_english_caste_certificate():
    reading = read_document(
        Kind.CASTE_CERTIFICATE,
        """GOVERNMENT OF JHARKHAND
        Office of the Circle Officer, Ranchi Sadar
        CASTE CERTIFICATE (For Scheduled Tribe)
        Certificate No. : JHCC/2023/0045612   Date: 12/03/2023
        This is to certify that Shri/Smt/Kumari SUNITA MURMU Daughter of Shri RAMESH MURMU
        of village Kanke, District Ranchi of the State of Jharkhand belongs to the MUNDA
        community which is recognised as a Scheduled Tribe.""",
    )
    assert reading.facts == {"is_scheduled_tribe": True}
    assert reading.fields == {
        "certificate_number": "JHCC/2023/0045612",
        "holder_name": "Sunita Murmu",
        "state": "Jharkhand",
        "district": "Ranchi",
        "category": "ST",
    }


def test_reads_a_hindi_caste_certificate_with_devanagari_digits():
    reading = read_document(
        Kind.CASTE_CERTIFICATE,
        """झारखण्ड सरकार
        जाति प्रमाण पत्र
        प्रमाण पत्र संख्या : JHCC/२०२३/००४५६१२
        प्रमाणित किया जाता है कि श्रीमती सुनीता मुर्मू पिता श्री रमेश मुर्मू, जिला राँची,
        मुण्डा जाति से हैं जो अनुसूचित जनजाति के रूप में मान्यता प्राप्त है।""",
    )
    assert reading.facts == {"is_scheduled_tribe": True}
    assert reading.fields["certificate_number"] == "JHCC/2023/0045612"
    assert reading.fields["holder_name"] == "सुनीता मुर्मू"
    assert reading.fields["state"] == "Jharkhand"
    assert reading.fields["district"] == "राँची"


def test_a_scheduled_caste_certificate_is_not_read_as_tribe():
    reading = read_document(
        Kind.CASTE_CERTIFICATE,
        "Government of Bihar. This is to certify that Ravi Kumar, son of ... belongs to a "
        "Scheduled Caste.",
    )
    assert not reading.readable
    assert "does not say Scheduled Tribe" in reading.problems[0]


def test_reads_income_and_financial_year():
    reading = read_document(
        Kind.INCOME_CERTIFICATE,
        "Government of Odisha. Income Certificate. Certificate No: OD-IC-88123. The annual "
        "income of the family for the financial year 2025-26 is Rs. 1,20,000/- (Rupees One "
        "Lakh Twenty Thousand only).",
    )
    assert reading.facts == {"family_income": 120000.0}
    assert reading.fields["financial_year"] == "2025-26"
    assert reading.fields["state"] == "Odisha"


def test_reads_income_without_a_currency_sign_but_not_a_year():
    reading = read_document(
        Kind.INCOME_CERTIFICATE,
        "Madhya Pradesh. वार्षिक आय वर्ष 2025 में 85000 है। वित्तीय वर्ष 2025-26",
    )
    assert reading.facts == {"family_income": 85000.0}
    assert reading.fields["financial_year"] == "2025-26"


def test_reads_a_marksheet_percentage_or_works_it_out():
    direct = read_document(
        Kind.BACHELORS_MARKSHEET,
        "Ranchi University. B.A. Final. Name: Birsa Oraon Roll No 1234. Aggregate: 64.5 %",
    )
    assert direct.facts == {"bachelors_marks_percent": 64.5}
    assert direct.fields["holder_name"] == "Birsa Oraon"
    worked = read_document(
        Kind.MASTERS_MARKSHEET,
        "Gondwana University. M.Sc. Grand Total 1134 / 1800 Result: PASS",
    )
    assert worked.facts == {"masters_marks_percent": 63.0}


def test_a_cgpa_marksheet_asks_for_the_conversion_certificate():
    reading = read_document(
        Kind.BACHELORS_MARKSHEET, "Some University. Semester VI. SGPA 7.8 CGPA 7.4 Result PASS"
    )
    assert not reading.readable
    assert "percentage conversion certificate" in reading.problems[0]


def test_state_names_match_whole_words_only():
    reading = read_document(
        Kind.CASTE_CERTIFICATE,
        "Government of Assam. District Goalpara. This is to certify that ... Scheduled Tribe",
    )
    assert reading.fields["state"] == "Assam"


# Encryption and storage


def test_encryption_round_trips_and_binds_the_document():
    settings = get_settings()
    blob = crypto.encrypt(settings, "doc-1", b"a photo")
    assert b"a photo" not in blob
    assert crypto.decrypt(settings, "doc-1", blob) == b"a photo"
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(settings, "doc-2", blob)
    tampered = blob[:-1] + bytes([blob[-1] ^ 1])
    with pytest.raises(crypto.DecryptionError):
        crypto.decrypt(settings, "doc-1", tampered)


async def test_file_store(tmp_path):
    files = FileStore(tmp_path)
    await files.put("a/b", b"data")
    assert await files.get("a/b") == b"data"
    assert (tmp_path / "a" / "b").stat().st_mode & 0o777 == 0o600
    await files.delete("a/b")
    with pytest.raises(ObjectNotFound):
        await files.get("a/b")
    with pytest.raises(ValueError):
        await files.put("../escape", b"x")


async def test_s3_store():
    with mock_aws():
        # The bucket does not exist yet: the store creates it on first use.
        s3 = S3Store(boto3.client("s3", region_name="ap-south-1"), "docs")
        await s3.put("students/x/y", b"cipher")
        assert await s3.get("students/x/y") == b"cipher"
        await s3.delete("students/x/y")
        with pytest.raises(ObjectNotFound):
            await s3.get("students/x/y")


# The API


async def test_a_certificate_in_the_edistrict_register_is_confirmed_at_once(
    client, sign_in, link_digilocker, store
):
    person = person_where(has_caste_certificate=True, tribe=lambda t: t is not None)
    tokens = await sign_in(f"+91{person.phone}")
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    await link_digilocker(auth, person)

    response = await upload(
        client, auth, "caste_certificate", await paper_text(person.phone, "caste")
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["readable"] is True
    assert body["verified_facts"] == ["is_scheduled_tribe"]
    assert body["document"]["status"] == "verified"
    assert "confirmed with the" in body["message"]

    verification = (await client.get("/v1/me/verification", headers=auth)).json()
    assert verification["facts"]["is_scheduled_tribe"]["source"] == "edistrict"
    assert verification["facts"]["is_scheduled_tribe"]["verified"] is True

    # The photo is stored encrypted, and the Student can see it through a short-lived link.
    (stored,) = [p for p in store.root.rglob("*") if p.is_file()]
    assert JPEG not in stored.read_bytes()
    link = (
        await client.get(f"/v1/me/documents/uploads/{body['document']['id']}/link", headers=auth)
    ).json()
    photo = await client.get(link["url"])
    assert photo.status_code == 200
    assert photo.content == JPEG
    assert photo.headers["cache-control"] == "private, no-store"


async def test_a_paper_certificate_goes_to_the_district_with_its_photo(
    client, sign_in, link_digilocker, official, store
):
    person = person_where(has_caste_certificate=False, tribe=lambda t: t is not None)
    tokens = await sign_in(f"+91{person.phone}")
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    await link_digilocker(auth, person)

    response = await upload(
        client, auth, "caste_certificate", await paper_text(person.phone, "caste")
    )
    body = response.json()
    assert body["verified_facts"] == []
    assert body["document"]["status"] == "with_reviewer"
    assert "e-District register" in body["message"]

    reviewer = await official("district", person.state.name, person.district)
    queue = (await client.get("/v1/review/exceptions", headers=reviewer)).json()
    (item,) = [i for i in queue if i["kind"] == "paper_certificate"]
    case = (await client.get(f"/v1/review/exceptions/{item['id']}", headers=reviewer)).json()
    assert case["photo"]["name"] == "caste certificate"
    assert case["photo"]["fields"]["category"] == "ST"
    assert case["copilot"]["headline"] == "A paper certificate no register could confirm"
    assert any("seal and signature" in line for line in case["copilot"]["look_at"])
    photo = await client.get(case["photo"]["url"])
    assert photo.content == JPEG

    decision = await client.post(
        f"/v1/review/exceptions/{item['id']}/decision",
        headers=reviewer,
        json={"decision": "confirm", "note": "Seal and signature checked against the register"},
    )
    assert decision.status_code == 200, decision.text
    (document,) = (await client.get("/v1/me/documents/uploads", headers=auth)).json()
    assert document["status"] == "accepted"
    verification = (await client.get("/v1/me/verification", headers=auth)).json()
    assert verification["facts"]["is_scheduled_tribe"]["source"] == "reviewer"

    async with get_sessionmaker()() as session:
        actions = (await session.scalars(select(AuditEvent.action))).all()
    assert "document.view" in actions
    assert "document.upload" in actions


async def test_without_digilocker_the_case_is_routed_by_the_certificate(
    client, auth, official, store
):
    person = person_where(has_caste_certificate=True, tribe=lambda t: t is not None)
    response = await upload(
        client, auth, "caste_certificate", await paper_text(person.phone, "caste")
    )
    body = response.json()
    assert body["document"]["status"] == "with_reviewer"
    assert "cannot yet check that it is yours" in body["message"]

    reviewer = await official("district", person.state.name, person.district)
    queue = (await client.get("/v1/review/exceptions", headers=reviewer)).json()
    assert [i["kind"] for i in queue] == ["unlinked_identity"]
    assert queue[0]["district"] == person.district


async def test_a_stale_income_certificate_asks_for_a_new_one(
    client, sign_in, link_digilocker, store
):
    person = person_where(has_income_certificate=True, stale_income_certificate=True)
    tokens = await sign_in(f"+91{person.phone}")
    auth = {"Authorization": f"Bearer {tokens['access_token']}"}
    await link_digilocker(auth, person)
    response = await upload(
        client, auth, "income_certificate", await paper_text(person.phone, "income")
    )
    body = response.json()
    assert body["document"]["status"] == "with_reviewer"
    assert "Apply for a new income certificate" in body["document"]["remedy"]


async def test_an_unreadable_photo_is_not_kept(client, auth, store):
    response = await upload(client, auth, "income_certificate", "blurry")
    assert response.status_code == 201
    body = response.json()
    assert body["readable"] is False
    assert body["document"] is None
    assert "daylight" in body["message"]
    assert not [p for p in store.root.rglob("*") if p.is_file()]


async def test_only_real_images_are_accepted(client, auth, store):
    text = "Aggregate 70 % Name: Test"
    wrong = await upload(client, auth, "bachelors_marksheet", text, b"GIF89a....", "image/gif")
    assert wrong.status_code == 422
    disguised = await upload(client, auth, "bachelors_marksheet", text, b"MZ\x90\x00", "image/png")
    assert disguised.status_code == 422
    assert "not the kind of image" in disguised.json()["detail"]


async def test_links_expire_and_belong_to_one_document(client, auth, store):
    response = await upload(client, auth, "bachelors_marksheet", "B.A. Aggregate: 71.2 %")
    document_id = response.json()["document"]["id"]
    link = (await client.get(f"/v1/me/documents/uploads/{document_id}/link", headers=auth)).json()
    token = link["url"].split("token=")[1]
    other = await client.get(f"/v1/documents/{uuid.uuid4()}/content?token={token}")
    assert other.status_code == 403
    forged = await client.get(f"/v1/documents/{document_id}/content?token={token}x")
    assert forged.status_code == 403


async def test_a_new_photo_replaces_one_not_yet_reviewed(client, auth, store):
    first = await upload(client, auth, "bachelors_marksheet", "B.A. Aggregate: 51.0 %")
    second = await upload(client, auth, "bachelors_marksheet", "B.A. Aggregate: 61.0 %")
    documents = (await client.get("/v1/me/documents/uploads", headers=auth)).json()
    assert [d["id"] for d in documents] == [second.json()["document"]["id"]]
    assert first.json()["document"]["id"] != documents[0]["id"]
    verification = (await client.get("/v1/me/verification", headers=auth)).json()
    assert verification["facts"]["bachelors_marks_percent"]["value"] == 61.0
    assert verification["facts"]["bachelors_marks_percent"]["source"] == "uploaded"


async def test_the_student_can_delete_a_photo(client, auth, store):
    response = await upload(client, auth, "bachelors_marksheet", "B.A. Aggregate: 71.2 %")
    document_id = response.json()["document"]["id"]
    link = (await client.get(f"/v1/me/documents/uploads/{document_id}/link", headers=auth)).json()
    deleted = await client.delete(f"/v1/me/documents/uploads/{document_id}", headers=auth)
    assert deleted.status_code == 204
    assert not [p for p in store.root.rglob("*") if p.is_file()]
    assert (await client.get(link["url"])).status_code == 410
    assert (await client.get("/v1/me/documents/uploads", headers=auth)).json() == []
    verification = (await client.get("/v1/me/verification", headers=auth)).json()
    assert verification["exceptions"] == []


async def test_photos_are_purged_after_their_retention_period(client, auth, store):
    await upload(client, auth, "bachelors_marksheet", "B.A. Aggregate: 71.2 %")
    async with get_sessionmaker()() as session:
        assert await purge_expired(session, store) == 0
        later = datetime.now(UTC) + timedelta(days=3 * 365)
        assert await purge_expired(session, store, later) == 1
        await session.commit()
        (document,) = (await session.scalars(select(UploadedDocument))).all()
    assert document.status == "deleted"
    assert document.object_key is None
    assert not [p for p in store.root.rglob("*") if p.is_file()]
