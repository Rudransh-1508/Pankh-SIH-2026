async def test_lists_the_five_mota_schemes(client):
    schemes = (await client.get("/v1/schemes")).json()
    assert [s["id"] for s in schemes] == ["pre_matric", "post_matric", "top_class", "nfst", "nos"]
    benefit = schemes[0]["benefits"][0]
    assert benefit["citation"]["url"].endswith(".pdf#page=4")


async def test_unknown_scheme_is_404(client):
    assert (await client.get("/v1/schemes/nope")).status_code == 404


async def test_fact_schema_describes_forms(client):
    specs = {spec["name"]: spec for spec in (await client.get("/v1/facts/schema")).json()}
    assert specs["family_income"]["kind"] == "number"
    level = specs["education_level"]
    assert level["kind"] == "choice"
    assert {"key": "class_9", "label": "Class IX"} in level["choices"]
    assert all(choice["key"] != "unknown" for choice in level["choices"])


async def test_lists_official_sources(client):
    sources = (await client.get("/v1/sources")).json()
    assert len(sources) == 10
    assert all(s["url"].startswith("https://tribal.nic.in/") for s in sources)


async def test_searches_top_class_institutes(client):
    results = (
        await client.get("/v1/institutes/top-class", params={"q": "technology delhi"})
    ).json()
    assert results[0]["name"] == "Indian Institute of Technology Delhi"
    assert results[0]["citation"]["clause"] == "S.No. 1"
