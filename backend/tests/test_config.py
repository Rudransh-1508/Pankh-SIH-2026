def test_host_database_urls_use_the_async_driver():
    from app.config import Settings

    for given in ("postgres://u:p@db:5432/pankh", "postgresql://u:p@db:5432/pankh"):
        assert Settings(database_url=given).database_url == "postgresql+asyncpg://u:p@db:5432/pankh"


def test_neon_urls_keep_tls_in_asyncpgs_spelling():
    from app.config import Settings

    neon = (
        "postgresql://pankh:secret@ep-quiet-sky-123.ap-southeast-1.aws.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )
    assert Settings(database_url=neon).database_url == (
        "postgresql+asyncpg://pankh:secret@ep-quiet-sky-123.ap-southeast-1.aws.neon.tech/neondb"
        "?ssl=require"
    )


def test_render_gives_the_public_address(monkeypatch):
    from app.config import Settings

    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://pankh-sih-api.onrender.com/")
    assert Settings().public_api_url == "https://pankh-sih-api.onrender.com"
    assert Settings(public_api_url="https://x.example").public_api_url == "https://x.example"
