"""Async persistence layer for the MMM Platform.

Default: SQLite via aiosqlite. When ``DATABASE_URL`` (or a Supabase
``postgresql://`` URL) is set, uses PostgreSQL via asyncpg. A single
SQLAlchemy model layer (``mmm.db.models``) backs both.
"""

from mmm.db.models import (
    ALL_MODELS,
    Base,
    BudgetOptimization,
    ChannelResult,
    Client,
    DataSource,
    Insight,
    MarketingData,
    Membership,
    ModelJob,
    Organization,
    Report,
    User,
)
from mmm.db.repo import (
    add_channel_results,
    add_insight,
    bulk_insert_marketing_data,
    create_budget_optimization,
    create_client,
    create_data_source,
    create_membership,
    create_model_job,
    create_organization,
    create_report,
    create_user,
    delete_client,
    get_channel_results,
    get_client,
    get_membership,
    get_model_job,
    get_organization,
    get_organization_by_slug,
    get_report,
    get_user,
    get_user_by_email,
    list_budget_optimizations,
    list_clients,
    list_data_sources,
    list_insights,
    list_memberships,
    list_model_jobs,
    list_reports,
    list_users,
    update_model_job,
)
from mmm.db.session import (
    close_db,
    get_engine,
    get_session,
    get_session_factory,
)
from mmm.db.session import (
    init_db as init_db,
)

__all__ = [
    "ALL_MODELS", "Base",
    "BudgetOptimization", "ChannelResult", "Client", "DataSource", "Insight",
    "MarketingData", "Membership", "ModelJob", "Organization", "Report", "User",
    "add_channel_results", "add_insight", "bulk_insert_marketing_data",
    "create_budget_optimization", "create_client", "create_data_source",
    "create_membership", "create_model_job", "create_organization", "create_report",
    "create_user", "delete_client", "get_channel_results", "get_client",
    "get_membership", "get_model_job", "get_organization", "get_organization_by_slug",
    "get_report", "get_user", "get_user_by_email", "list_budget_optimizations",
    "list_clients", "list_data_sources", "list_insights", "list_memberships",
    "list_model_jobs", "list_reports", "list_users", "update_model_job",
    "close_db", "get_engine", "get_session", "get_session_factory", "init_db",
]
