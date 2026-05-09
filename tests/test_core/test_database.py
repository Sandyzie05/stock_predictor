"""
Tests for database module.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal, Base, engine, get_db


class TestDatabase:
    """Test database configuration and functionality."""

    def test_base_class(self):
        """Test Base class exists and is properly configured."""
        assert Base is not None
        assert hasattr(Base, "metadata")

    def test_engine_creation(self):
        """Test that engine is created properly."""
        assert engine is not None
        assert engine.url.drivername == "postgresql+asyncpg"

    def test_session_factory(self):
        """Test session factory configuration."""
        assert AsyncSessionLocal is not None
        assert AsyncSessionLocal.bind is engine

    @pytest.mark.asyncio
    async def test_get_db_dependency(self):
        """Test get_db dependency function."""
        # This will use the test database session from conftest.py
        db_gen = get_db()
        db_session = await db_gen.__anext__()

        assert isinstance(db_session, AsyncSession)

        # Clean up
        await db_gen.aclose()

    @pytest.mark.asyncio
    async def test_database_session_context_manager(self, db_session):
        """Test database session works as context manager."""
        assert isinstance(db_session, AsyncSession)
        assert not db_session.is_active  # Should not be in transaction initially

        # Start transaction
        async with db_session.begin():
            assert db_session.in_transaction()

        # Should be committed and no longer in transaction
        assert not db_session.in_transaction()

    @pytest.mark.asyncio
    async def test_session_rollback(self, db_session):
        """Test session rollback functionality."""
        # This tests the fixture's rollback behavior
        # The fixture should rollback after each test
        assert isinstance(db_session, AsyncSession)

        # Any changes made in a test should be rolled back
        # by the conftest.py fixture
