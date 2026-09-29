"""Run the chasing worker. Usage (from backend/): uv run python -m app.chasing.worker"""

import asyncio

from temporalio.client import Client
from temporalio.worker import Worker

from app.chasing.workflows import ChaseStudent, check_student_activity
from app.config import get_settings


async def main() -> None:
    settings = get_settings()
    if not settings.temporal_address:
        raise SystemExit("Set PANKH_TEMPORAL_ADDRESS, for example localhost:7233")
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.chasing_task_queue,
        workflows=[ChaseStudent],
        activities=[check_student_activity],
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
