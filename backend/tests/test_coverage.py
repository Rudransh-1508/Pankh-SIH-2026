async def test_ministry_finds_unreached_students(client, official):
    ministry = await official("ministry")
    assert (await client.get("/v1/ministry/coverage", headers=ministry)).status_code == 404

    run = await client.post("/v1/ministry/coverage/runs", headers=ministry)
    assert run.status_code == 201, run.text
    totals = run.json()["totals"]
    assert totals["enrolled"] == totals["reached"] + totals["possible"] + totals["unreached"]
    assert 0 < totals["coverage"] < 1

    coverage = (await client.get("/v1/ministry/coverage", headers=ministry)).json()
    jharkhand = next(s for s in coverage["states"] if s["state"] == "Jharkhand")
    assert jharkhand["official"]["total"] > 0  # the ministry's published beneficiaries
    assert jharkhand["districts"]

    unreached = (
        await client.get(
            "/v1/ministry/coverage/unreached", params={"state": "Odisha"}, headers=ministry
        )
    ).json()
    assert unreached["total"] > 0
    first = unreached["items"][0]
    assert first["state"] == "Odisha"
    assert first["likely_schemes"]


async def test_state_officials_see_only_their_state(client, official):
    ministry = await official("ministry")
    await client.post("/v1/ministry/coverage/runs", headers=ministry)
    state = await official("state", "Jharkhand")
    coverage = (await client.get("/v1/ministry/coverage", headers=state)).json()
    assert [s["state"] for s in coverage["states"]] == ["Jharkhand"]
    assert coverage["totals"]["enrolled"] == coverage["states"][0]["enrolled"]
    assert (await client.post("/v1/ministry/coverage/runs", headers=state)).status_code == 403
    district = await official("district", "Jharkhand", "Dumka")
    assert (await client.get("/v1/ministry/coverage", headers=district)).status_code == 403


async def test_pipeline_counts_nsp_applications_by_status(client, official):
    ministry = await official("ministry")
    body = (await client.get("/v1/ministry/pipeline", headers=ministry)).json()
    assert body["states"]
    assert sum(body["states"][0]["statuses"].values()) == body["states"][0]["total"]


async def test_official_figures_are_published_data(client, official):
    ministry = await official("ministry")
    rows = (await client.get("/v1/ministry/official-figures", headers=ministry)).json()["rows"]
    assert any(r["state"] == "Jharkhand" and r["scheme"] == "post_matric" for r in rows)
