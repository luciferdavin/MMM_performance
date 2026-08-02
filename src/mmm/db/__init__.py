"""Async persistence layer for the MMM Platform.

Default: SQLite via aiosqlite. When ``DATABASE_URL`` is set, uses Supabase
Postgres via asyncpg.
"""
from mmm.db.models import Base, ChannelResult, Client, DataSource, ModelJob
from mmm.db.repo import (
    add_channel_results,
    create_client,
    create_model_job,
    delete_client,
    get_channel_results,
    get_client,
    get_model_job,
    list_clients,
    list_model_jobs,
    update_model_job,
)
from mmm.db.session import close_db, get_engine, get_session, init_db
