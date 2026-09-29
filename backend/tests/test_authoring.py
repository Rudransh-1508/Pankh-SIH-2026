import yaml


def pdf(*lines: str) -> bytes:
    """A one-page PDF with a text layer, built by hand so tests need no PDF library."""
    text = "\n".join(
        f"BT /F1 11 Tf 50 {780 - 16 * i} Td ({line}) Tj ET" for i, line in enumerate(lines)
    ).encode()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length %d >>\nstream\n" % len(text) + text + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1,
        xref,
    )
    return bytes(out)


REVISED = pdf(
    "Central Sector Scheme of Scholarship for College and University Students.",
    "v. Students with gross parental/family income upto Rs. 6 lakh per annum are",
    "eligible for scholarship under the scheme.",
)


async def check(client, headers, data=REVISED, scheme="csss"):
    return await client.post(
        "/v1/ministry/rule-drafts",
        headers=headers,
        data={"scheme_id": scheme, "title": "CSSS guidelines 2027"},
        files={"file": ("guideline.pdf", data, "application/pdf")},
    )


async def test_a_new_guideline_drafts_a_change_that_is_approved_as_a_file(client, official):
    ministry = await official("ministry")
    response = await check(client, ministry)
    assert response.status_code == 201, response.text
    (draft,) = response.json()
    assert draft["parameter"] == "csss.income_ceiling"
    assert (draft["current_value"], draft["found_value"]) == (450000, 600000)
    assert draft["status"] == "proposed"
    assert draft["page"] == 1
    assert "Rs. 6 lakh per annum" in draft["excerpt"]

    no_date = await client.post(
        f"/v1/ministry/rule-drafts/{draft['id']}/decision",
        headers=ministry,
        json={"decision": "approve"},
    )
    assert no_date.status_code == 422
    too_early = await client.post(
        f"/v1/ministry/rule-drafts/{draft['id']}/decision",
        headers=ministry,
        json={"decision": "approve", "effective_from": "2020-07-01"},
    )
    assert too_early.status_code == 422
    approved = await client.post(
        f"/v1/ministry/rule-drafts/{draft['id']}/decision",
        headers=ministry,
        json={"decision": "approve", "effective_from": "2027-07-01", "note": "Revised ceiling"},
    )
    assert approved.json()["status"] == "approved"
    patch = await client.get(f"/v1/ministry/rule-drafts/{draft['id']}/patch", headers=ministry)
    data = yaml.safe_load(patch.text)
    assert [v["value"] for v in data["values"].values()] == [450000, 600000]
    assert data["reference"].endswith("CSSS guidelines 2027, page 1")


async def test_a_guideline_that_agrees_with_the_rules_only_confirms_them(client, official):
    ministry = await official("ministry")
    same = pdf("v. Students with gross parental/family income upto Rs. 4.5 lakh per annum.")
    (draft,) = (await check(client, ministry, same)).json()
    assert draft["status"] == "matches"
    decided = await client.post(
        f"/v1/ministry/rule-drafts/{draft['id']}/decision",
        headers=ministry,
        json={"decision": "reject"},
    )
    assert decided.status_code == 409


async def test_only_the_ministry_changes_rules_and_only_from_readable_pdfs(client, official):
    state = await official("state", "Jharkhand")
    assert (await check(client, state)).status_code == 403
    ministry = await official("ministry")
    assert (await check(client, ministry, b"not a pdf")).status_code == 422
    assert (await check(client, ministry, scheme="nope")).status_code == 422
