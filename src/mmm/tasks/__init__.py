"""Celery tasks for the MMM platform.

Register every task module here so that
``app.autodiscover_tasks`` and ``include=[...]`` find them.

Module listing:
    train   — background MMM model training
"""
try:
    from mmm.tasks.train import train_model_job  # noqa: F401 — re-export for Celery autodiscovery
    __all__ = ["train_model_job"]
except ImportError:
    # celery (or another runtime dependency) is not installed — the task
    # modules are still importable for static analysis and documentation
    # purposes, but the tasks themselves cannot run.
    __all__ = []
