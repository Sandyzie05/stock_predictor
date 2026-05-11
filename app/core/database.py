"""
Database configuration and session management.
"""

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import (AsyncSession, async_sessionmaker,
                                    create_async_engine)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=3600,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all database models."""


async def get_db():
    """Get database session dependency."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_tables():
    """Create database tables."""
    import app.models  # noqa: F401  Ensures model metadata is registered.

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if engine.url.get_backend_name().startswith("sqlite"):
            await conn.run_sync(_ensure_sqlite_schema_compatibility)


def _ensure_sqlite_schema_compatibility(connection):
    """Backfill additive columns for local SQLite databases created by older app versions."""
    tables = {
        "daily_prediction_snapshot": Base.metadata.tables["daily_prediction_snapshot"],
        "daily_prediction_scenario": Base.metadata.tables["daily_prediction_scenario"],
    }
    inspector = inspect(connection)
    existing_tables = set(inspector.get_table_names())

    for table_name, table in tables.items():
        if table_name not in existing_tables:
            continue

        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        for column in table.columns:
            if column.name in existing_columns:
                continue
            definition = _sqlite_column_definition(column)
            connection.execute(
                text(f"ALTER TABLE {table_name} ADD COLUMN {column.name} {definition}")
            )


def _sqlite_column_definition(column) -> str:
    compiled_type = column.type.compile(dialect=engine.dialect)
    default_clause = ""
    if not column.nullable:
        if compiled_type.upper().startswith(("VARCHAR", "TEXT", "CHAR")):
            default_clause = " NOT NULL DEFAULT ''"
        elif compiled_type.upper().startswith(("INTEGER", "NUMERIC", "FLOAT", "REAL")):
            default_clause = " NOT NULL DEFAULT 0"
        elif compiled_type.upper().startswith("DATETIME"):
            default_clause = " NOT NULL DEFAULT CURRENT_TIMESTAMP"
    return f"{compiled_type}{default_clause}"
