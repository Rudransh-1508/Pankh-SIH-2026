async def test_lists_the_five_mota_schemes_then_the_catalogue(client):
    schemes = (await client.get("/v1/schemes")).json()
    assert [s["id"] for s in schemes if s["kind"] == "mota"] == [
        "pre_matric",
        "post_matric",
        "top_class",
        "nfst",
        "nos",
    ]
    assert {s["id"] for s in schemes if s["kind"] == "catalogue"} == {"csss", "pragati", "nmmss"}
    benefit = schemes[0]["benefits"][0]
    assert benefit["citation"]["url"].endswith(".pdf#page=4")


async def test_unknown_scheme_is_404(client):
    assert (await client.get("/v1/schemes/nope")).status_code == 404


async def test_fact_schema_describes_forms(client):
    specs = {spec["name"]: spec for spec in (await client.get("/v1/facts/schema")).json()}
    assert specs["family_income"]["kind"] == "number"
    level = specs["education_level"]
    assert level["kind"] == "choice"
    class_9 = next(c for c in level["choices"] if c["key"] == "class_9")
    assert class_9["labels"] == {"en": "Class IX", "hi": "कक्षा 9"}
    assert specs["is_scheduled_tribe"]["question"]["hi"].startswith("क्या आप")
    assert all(choice["key"] != "unknown" for choice in level["choices"])


async def test_lists_official_sources(client):
    sources = (await client.get("/v1/sources")).json()
    assert len(sources) == 13
    assert all(s["url"].startswith("https://") for s in sources)
    assert sum(s["url"].startswith("https://tribal.nic.in/") for s in sources) == 10


async def test_searches_top_class_institutes(client):
    results = (
        await client.get("/v1/institutes/top-class", params={"q": "technology delhi"})
    ).json()
    assert results[0]["name"] == "Indian Institute of Technology Delhi"
    assert results[0]["citation"]["clause"] == "S.No. 1"


async def test_lists_rules_with_their_values_for_the_year(client):
    body = (await client.get("/v1/rules", params={"academic_year": 2024})).json()
    nfst = next(s for s in body["schemes"] if s["scheme"]["id"] == "nfst")
    titles = [rule["title"] for rule in nfst["rules"]]
    assert "Aged 36 or under on 1 July" in titles
    assert all(
        rule["citation"]["url"].startswith("https://tribal.nic.in/") for rule in nfst["rules"]
    )
