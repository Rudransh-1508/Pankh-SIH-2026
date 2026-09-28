from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

from app.db import Base, get_engine


async def test_migrations_match_the_models():
    async with get_engine().connect() as connection:
        diff = await connection.run_sync(
            lambda sync: compare_metadata(MigrationContext.configure(sync), Base.metadata)
        )
    assert diff == []
