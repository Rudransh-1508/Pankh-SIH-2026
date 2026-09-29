"""Deleting document photos past their retention date, every day, as a durable workflow."""

from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

PURGE_EVERY = timedelta(days=1)
RUNS_PER_HISTORY = 30  # then continue as new, keeping the workflow's history small
WORKFLOW_ID = "purge-expired-photos"


@activity.defn
async def purge_expired_activity() -> int:
    from app.config import get_settings
    from app.db import get_sessionmaker
    from app.documents.agent import purge_expired
    from app.documents.storage import object_store

    async with get_sessionmaker()() as session:
        deleted = await purge_expired(session, object_store(get_settings()))
        await session.commit()
    return deleted


@workflow.defn
class PurgeExpiredPhotos:
    @workflow.run
    async def run(self) -> None:
        for _ in range(RUNS_PER_HISTORY):
            await workflow.execute_activity(
                purge_expired_activity,
                start_to_close_timeout=timedelta(minutes=10),
                retry_policy=RetryPolicy(maximum_attempts=5, initial_interval=timedelta(minutes=5)),
            )
            await workflow.sleep(PURGE_EVERY)
        workflow.continue_as_new()
