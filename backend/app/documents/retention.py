"""Delete Uploaded Document photos past their retention date. Run daily, for example from cron:

uv run python -m app.documents.retention
"""

import asyncio

from app.config import get_settings
from app.db import get_engine, get_sessionmaker
from app.documents.agent import purge_expired
from app.documents.storage import object_store


async def main() -> None:
    settings = get_settings()
    async with get_sessionmaker()() as session:
        deleted = await purge_expired(session, object_store(settings))
        await session.commit()
    await get_engine().dispose()
    print(f"Deleted {deleted} photo(s) past their retention date.")


if __name__ == "__main__":
    asyncio.run(main())
