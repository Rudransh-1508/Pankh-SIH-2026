"""The chasing agent as a durable Temporal workflow: check a Student every day, for as long as
they have applications in flight. Temporal keeps the schedule through restarts and deploys and
retries checks when a system of record is down."""

from datetime import timedelta

from temporalio import activity, workflow
from temporalio.common import RetryPolicy

CHECK_EVERY = timedelta(days=1)
CHECKS_PER_RUN = 30  # then continue as new, keeping the workflow's history small


@activity.defn
async def check_student_activity(student_id: str) -> dict[str, int]:
    import uuid

    import httpx

    from app.auth.sms import get_sms_sender
    from app.chasing.service import check_student
    from app.config import get_settings
    from app.db import get_sessionmaker

    async with get_sessionmaker()() as session, httpx.AsyncClient(timeout=30) as http:
        result = await check_student(
            session, get_settings(), http, get_sms_sender(), uuid.UUID(student_id)
        )
        await session.commit()
    return {"sent": result.sent_to_student, "proposed": result.proposed_to_offices}


@workflow.defn
class ChaseStudent:
    @workflow.run
    async def run(self, student_id: str) -> None:
        for _ in range(CHECKS_PER_RUN):
            await workflow.execute_activity(
                check_student_activity,
                student_id,
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=RetryPolicy(maximum_attempts=5, initial_interval=timedelta(minutes=1)),
            )
            await workflow.sleep(CHECK_EVERY)
        workflow.continue_as_new(student_id)


async def start_chasing(student_id: str) -> None:
    """Start chasing a Student, once. Does nothing when Temporal is not configured."""
    import logging

    from temporalio.client import Client
    from temporalio.common import WorkflowIDConflictPolicy

    from app.config import get_settings

    settings = get_settings()
    if not settings.temporal_address:
        return
    try:
        client = await Client.connect(
            settings.temporal_address, namespace=settings.temporal_namespace
        )
        await client.start_workflow(
            ChaseStudent.run,
            student_id,
            id=f"chase-{student_id}",
            task_queue=settings.chasing_task_queue,
            id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        )
    except Exception:  # scheduling must never break the Student's request
        logging.getLogger(__name__).exception("Could not start chasing %s", student_id)
