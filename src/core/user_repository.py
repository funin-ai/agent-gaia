"""User repository for database operations."""

import uuid
from datetime import datetime, timezone
from typing import Optional

from src.core.database import get_db_pool
from src.core.auth import User, UserCreate
from src.utils.logger import logger


class UserRepository:
    """Repository for user database operations."""

    @staticmethod
    async def create_tables():
        """Create users table if not exists."""
        pool = get_db_pool()

        try:
            async with pool.connection() as conn:
                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        email VARCHAR(255) UNIQUE NOT NULL,
                        name VARCHAR(255),
                        picture TEXT,
                        provider VARCHAR(50) NOT NULL,
                        provider_id VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP WITH TIME ZONE,
                        is_active BOOLEAN DEFAULT true,
                        UNIQUE(provider, provider_id)
                    );

                    CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
                    CREATE INDEX IF NOT EXISTS idx_users_provider ON users(provider, provider_id);
                """)
                logger.info("Users table created/verified")
        except Exception as e:
            logger.error(f"Failed to create users table: {e}")
            raise

    @staticmethod
    async def get_by_id(user_id: str) -> Optional[User]:
        """Get user by ID."""
        pool = get_db_pool()

        try:
            async with pool.connection() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM users WHERE id = $1 AND is_active = true",
                    uuid.UUID(user_id)
                )

                if row:
                    return User(
                        id=str(row['id']),
                        email=row['email'],
                        name=row['name'],
                        picture=row['picture'],
                        provider=row['provider'],
                        provider_id=row['provider_id'],
                        created_at=row['created_at'],
                        last_login=row['last_login'],
                        is_active=row['is_active']
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get user by id: {e}")
            return None

    @staticmethod
    async def get_by_email(email: str) -> Optional[User]:
        """Get user by email."""
        pool = get_db_pool()

        try:
            async with pool.connection() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM users WHERE email = $1 AND is_active = true",
                    email
                )

                if row:
                    return User(
                        id=str(row['id']),
                        email=row['email'],
                        name=row['name'],
                        picture=row['picture'],
                        provider=row['provider'],
                        provider_id=row['provider_id'],
                        created_at=row['created_at'],
                        last_login=row['last_login'],
                        is_active=row['is_active']
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get user by email: {e}")
            return None

    @staticmethod
    async def get_by_provider(provider: str, provider_id: str) -> Optional[User]:
        """Get user by OAuth provider and provider ID."""
        pool = get_db_pool()

        try:
            async with pool.connection() as conn:
                row = await conn.fetchrow(
                    "SELECT * FROM users WHERE provider = $1 AND provider_id = $2 AND is_active = true",
                    provider, provider_id
                )

                if row:
                    return User(
                        id=str(row['id']),
                        email=row['email'],
                        name=row['name'],
                        picture=row['picture'],
                        provider=row['provider'],
                        provider_id=row['provider_id'],
                        created_at=row['created_at'],
                        last_login=row['last_login'],
                        is_active=row['is_active']
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to get user by provider: {e}")
            return None

    @staticmethod
    async def create(user_data: UserCreate) -> Optional[User]:
        """Create a new user."""
        pool = get_db_pool()

        try:
            async with pool.connection() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO users (email, name, picture, provider, provider_id)
                    VALUES ($1, $2, $3, $4, $5)
                    RETURNING *
                """, user_data.email, user_data.name, user_data.picture,
                    user_data.provider, user_data.provider_id)

                if row:
                    logger.info(f"Created new user: {user_data.email} via {user_data.provider}")
                    return User(
                        id=str(row['id']),
                        email=row['email'],
                        name=row['name'],
                        picture=row['picture'],
                        provider=row['provider'],
                        provider_id=row['provider_id'],
                        created_at=row['created_at'],
                        last_login=row['last_login'],
                        is_active=row['is_active']
                    )
                return None
        except Exception as e:
            logger.error(f"Failed to create user: {e}")
            return None

    @staticmethod
    async def update_last_login(user_id: str) -> bool:
        """Update user's last login timestamp."""
        pool = get_db_pool()

        try:
            async with pool.connection() as conn:
                await conn.execute(
                    "UPDATE users SET last_login = $1 WHERE id = $2",
                    datetime.now(timezone.utc), uuid.UUID(user_id)
                )
                return True
        except Exception as e:
            logger.error(f"Failed to update last login: {e}")
            return False

    @staticmethod
    async def upsert_from_oauth(user_data: UserCreate) -> Optional[User]:
        """Create or update user from OAuth data.

        If user exists with same provider/provider_id, update their info.
        If user exists with same email but different provider, link accounts.
        Otherwise create new user.
        """
        pool = get_db_pool()

        try:
            # First check if user exists with this provider
            existing = await UserRepository.get_by_provider(
                user_data.provider, user_data.provider_id
            )

            if existing:
                # Update last login and return
                await UserRepository.update_last_login(existing.id)
                # Update name/picture if changed
                async with pool.connection() as conn:
                    await conn.execute("""
                        UPDATE users SET name = $1, picture = $2, last_login = $3
                        WHERE id = $4
                    """, user_data.name, user_data.picture,
                        datetime.now(timezone.utc), uuid.UUID(existing.id))

                return await UserRepository.get_by_id(existing.id)

            # Check if email exists (link accounts scenario)
            existing_email = await UserRepository.get_by_email(user_data.email)
            if existing_email:
                # User logged in with different provider but same email
                # For security, we don't auto-link - create new record
                logger.warning(
                    f"User {user_data.email} exists with provider {existing_email.provider}, "
                    f"attempting login with {user_data.provider}"
                )

            # Create new user
            return await UserRepository.create(user_data)

        except Exception as e:
            logger.error(f"Failed to upsert user from OAuth: {e}")
            return None
