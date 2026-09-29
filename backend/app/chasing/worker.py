"""Run the worker for Pankh's long-running work: chasing Students and deleting expired photos.
Usage (from backend/): uv run python -m app.chasing.worker"""

import asyncio

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.worker import Worker

from app.chasing.workflows import ChaseStudent, check_student_activity
from app.config import get_settings
from app.documents.workflows import WORKFLOW_ID, PurgeExpiredPhotos, purge_expired_activity


async def main() -> None:
    settings = get_settings()
    if not settings.temporal_address:
        raise SystemExit("Set PANKH_TEMPORAL_ADDRESS, for example localhost:7233")
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=settings.chasing_task_queue,
        workflows=[ChaseStudent, PurgeExpiredPhotos],
        activities=[check_student_activity, purge_expired_activity],
    )
    # One daily purge for the whole deployment, however many workers start.
    await client.start_workflow(
        PurgeExpiredPhotos.run,
        id=WORKFLOW_ID,
        task_queue=settings.chasing_task_queue,
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
