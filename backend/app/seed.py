"""Create the demo officials. Safe to run more than once.

Usage (from backend/): uv run python -m app.seed
"""

import asyncio

from sqlalchemy import select

from app.db import get_engine, get_sessionmaker
from app.models import Official

DEMO_OFFICIALS = (
    ("+919000000001", "Ministry of Tribal Affairs (demo)", "ministry", None, None),
    ("+919000000002", "Jharkhand Tribal Welfare Department (demo)", "state", "Jharkhand", None),
    ("+919000000003", "District Welfare Officer, Dumka (demo)", "district", "Jharkhand", "Dumka"),
    (
        "+919000000004",
        "District Welfare Officer, Mayurbhanj (demo)",
        "district",
        "Odisha",
        "Mayurbhanj",
    ),
)


async def seed() -> None:
    async with get_sessionmaker()() as session:
        for phone, name, level, state, district in DEMO_OFFICIALS:
            official = await session.scalar(select(Official).where(Official.phone == phone))
            if official is None:
                official = Official(phone=phone)
                session.add(official)
            official.name, official.level, official.state, official.district = (
                name,
                level,
                state,
                district,
            )
        await session.commit()
    await get_engine().dispose()
    for phone, name, *_ in DEMO_OFFICIALS:
        print(f"{phone}  {name}")


if __name__ == "__main__":
    asyncio.run(seed())
