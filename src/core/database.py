"""Database connection management with asyncpg."""

import asyncio
from typing import Optional
from contextlib import asynccontextmanager

import asyncpg

from src.core.settings import get_settings
from src.utils.logger import logger


class DatabasePool:
    """Async PostgreSQL connection pool manager."""

    _instance: Optional["DatabasePool"] = None
    _pool: Optional[asyncpg.Pool] = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_pool(self) -> asyncpg.Pool:
        """Get or create database connection pool.

        Returns:
            asyncpg connection pool
        """
        if self._pool is None:
            async with self._lock:
                if self._pool is None:
                    settings = get_settings()
                    db = settings.database
                    try:
                        self._pool = await asyncpg.create_pool(
                            host=db.host,
                            port=db.port,
                            database=db.database,
                            user=db.user,
                            password=db.password,
                            min_size=db.min_pool_size,
                            max_size=db.max_pool_size,
                        )
                        logger.info(f"Database pool created: {db.host}:{db.port}/{db.database}")
                    except Exception as e:
                        logger.error(f"Failed to create database pool: {e}")
                        raise
        return self._pool

    @asynccontextmanager
    async def connection(self):
        """Get a connection from the pool.

        Yields:
            asyncpg connection
        """
        pool = await self.get_pool()
        async with pool.acquire() as conn:
            yield conn

    async def close(self):
        """Close the database pool."""
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
            logger.info("Database pool closed")


# Global database pool instance
_db_pool: Optional[DatabasePool] = None


def get_db_pool() -> DatabasePool:
    """Get or create global database pool.

    Returns:
        DatabasePool instance
    """
    global _db_pool
    if _db_pool is None:
        _db_pool = DatabasePool()
    return _db_pool


async def init_database():
    """Initialize database connection pool."""
    pool = get_db_pool()
    await pool.get_pool()


async def close_database():
    """Close database connection pool."""
    pool = get_db_pool()
    await pool.close()
