"""Celery application instance, queue routing, and task-enqueue helpers.

Broker & result backend: Redis (``REDIS_URL``).
Workers must consume only the queues relevant to their role.

    mmm-worker -Q training          # GPU / CPU model training
    mmm-worker -Q data_sync         # connector sync tasks
    mmm-worker -Q reports           # PDF / email report tasks

See ``docs/02-trd.md`` §11 for the full topology and priority model.
"""
from __future__ import annotations

import logging
from typing import Any

from celery import Celery

from mmm.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Queue constants
# ---------------------------------------------------------------------------
QUEUE_TRAINING = "training"

# ---------------------------------------------------------------------------
# Per-queue routing table
#
# Celery message priority (Redis broker): 0 = highest, 9 = lowest.
# Training is high priority with a generous timeout for PyMC sampling.
# ---------------------------------------------------------------------------
_ROUTES: dict[str, dict[str, Any]] = {
    "mmm.tasks.train.train_model_job": {
        "queue": QUEUE_TRAINING,
        "routing_key": "train.model_job",
        "priority": 0,
        "time_limit": 1200,          # 20 min hard
        "soft_time_limit": 1080,     # 18 min soft → raises SoftTimeLimitExceeded
    },
}


# ---------------------------------------------------------------------------
# Celery application
# ---------------------------------------------------------------------------
def create_celery_app() -> Celery:
    """Build and configure the Celery application.

    Configuration highlights (``docs/02-trd.md`` §11.2-11.3):

    * ``task_acks_late`` + ``prefetch_multiplier=1`` — a long-running training
      job is only acknowledged after success, and a worker never pulls more
      than one job at a time.
    * ``task_reject_on_worker_lost`` — a killed/restarted worker requeues the
      in-progress task instead of losing it.
    * Redis is used for both the broker and the result backend (short TTL;
      heavy payloads live in the database).
    """
    settings = get_settings()

    app = Celery(
        "mmm",
        broker=settings.redis_url,
        backend=settings.redis_url,
        include=[
            "mmm.tasks.train",
        ],
    )

    app.conf.update(
        # --- Serialization ---
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        # --- Worker prefetch (§11.2) ---
        task_acks_late=True,
        task_reject_on_worker_lost=True,
        worker_prefetch_multiplier=1,
        # --- Task routing (queue + priority + time limits) ---
        task_routes=_ROUTES,
        # --- Result backend ---
        result_expires=3600,
    )

    return app


celery_app = create_celery_app()


# ---------------------------------------------------------------------------
# Enqueue helpers
# ---------------------------------------------------------------------------

def enqueue(
    task_name: str,
    args: tuple[Any, ...] = (),
    kwargs: dict[str, Any] | None = None,
    queue: str | None = None,
    priority: int | None = None,
) -> Any:
    """Enqueue an arbitrary task by its fully-qualified Celery name.

    Use this when callers need explicit control over routing.  For the common
    case of scheduling a training job prefer :func:`enqueue_train_job`.

    Returns the :class:`~celery.result.AsyncResult` — the caller can hold
    the handle to poll status or chain further work.
    """
    return celery_app.send_task(
        task_name,
        args=args,
        kwargs=kwargs or {},
        queue=queue,
        priority=priority,
    )


def enqueue_train_job(
    model_job_id: str,
    config: dict[str, Any] | None = None,
) -> Any:
    """Schedule a model training job on the ``training`` queue."""
    return celery_app.send_task(
        "mmm.tasks.train.train_model_job",
        kwargs={"model_job_id": model_job_id, "config": config},
        queue=QUEUE_TRAINING,
        priority=0,
    )

