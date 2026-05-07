"""
Database connection and session management for FinBot
"""

from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, select
import logging
import hashlib

from src.core.config import settings
from src.models.database import Base, User, UserRole

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations"""

    @staticmethod
    def _mask_db_url(url: str) -> str:
        """Mask DB password when logging connection URLs."""
        if "://" not in url or "@" not in url:
            return url

        scheme, remainder = url.split("://", 1)
        credentials, host_part = remainder.split("@", 1)
        if ":" in credentials:
            username, _ = credentials.split(":", 1)
            credentials = f"{username}:***"
        return f"{scheme}://{credentials}@{host_part}"
    
    def __init__(self):
        logger.info("🔧 Initializing DatabaseManager...")
        logger.info(f"📋 Database settings:")
        logger.info(f"   Host: {settings.postgres_host}")
        logger.info(f"   Port: {settings.postgres_port}")
        logger.info(f"   User: {settings.postgres_user}")
        logger.info(f"   Database: {settings.postgres_database}")
        logger.info(f"   Password: {'***' if settings.postgres_password else 'None'}")
        
        # Create async engine for FastAPI
        async_url = settings.async_database_url
        sync_url = settings.database_url
        logger.info(f"🔗 Async URL: {self._mask_db_url(async_url)}")
        logger.info(f"🔗 Sync URL: {self._mask_db_url(sync_url)}")
        
        self.async_engine = create_async_engine(
            async_url,
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow,
            pool_timeout=settings.pool_timeout,
            connect_args={"ssl": False},
            echo=False  # Set to True for SQL query logging
        )
        
        # Create sync engine for migrations
        self.sync_engine = create_engine(
            settings.database_url,
            pool_size=settings.pool_size,
            max_overflow=settings.max_overflow,
            pool_timeout=settings.pool_timeout,
            connect_args={"sslmode": "disable"},
            echo=False
        )
        
        # Session makers
        self.async_session = async_sessionmaker(
            bind=self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        self.sync_session = sessionmaker(
            bind=self.sync_engine,
            autocommit=False,
            autoflush=False
        )
    
    async def initialize_database(self):
        """Initialize database tables (without seeding demo users)"""
        try:
            logger.info("Initializing database...")
            logger.info(f"🔗 Using async database URL: {self._mask_db_url(settings.async_database_url)}")
            logger.info(f"🔗 Using sync database URL: {self._mask_db_url(settings.database_url)}")
            
            # Create all tables using async engine  
            async with self.async_engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("✅ Database tables created successfully")
            logger.info("📝 To seed demo users, run: python scripts/seed_demo_users.py")
            
            logger.info("✅ Database initialization completed")
            return True
            
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
            return False
    
    async def seed_demo_users(self):
        logger.info("🌱 Starting demo user seeding...")
        demo_users = [
        {
            "username": "john.employee",
            "email": "john.employee@finsolve.com",
            "full_name": "John Employee",
            "role": UserRole.EMPLOYEE
        },
        {
            "username": "sarah.finance",
            "email": "sarah.finance@finsolve.com",
            "full_name": "Sarah Finance",
            "role": UserRole.FINANCE
        },
        {
            "username": "mike.engineer",
            "email": "mike.engineer@finsolve.com",
            "full_name": "Mike Engineer",
            "role": UserRole.ENGINEERING
        },
        {
            "username": "lisa.marketing",
            "email": "lisa.marketing@finsolve.com",
            "full_name": "Lisa Marketing",
            "role": UserRole.MARKETING
        },
        {
            "username": "robert.hr",
            "email": "robert.hr@finsolve.com",
            "full_name": "Robert HR",
            "role": UserRole.HR
        },
        {
            "username": "maria.ceo",
            "email": "maria.ceo@finsolve.com",
            "full_name": "Maria CEO",
            "role": UserRole.C_LEVEL
        }
    ]
        password_hash = self._hash_password("demo123")
        async with self.async_session() as session:
            try:
                for user_data in demo_users:

                    logger.info(
                        f"Checking user: {user_data['username']}"
                    )

                    result = await session.execute(
                        select(User).where(
                            User.username == user_data["username"]
                        )
                    )

                    existing_user = result.scalar_one_or_none()

                    if existing_user:
                        logger.info(
                            f"⚠️ User already exists: "
                            f"{user_data['username']}"
                        )
                        continue

                    user = User(
                        username=user_data["username"],
                        email=user_data["email"],
                        full_name=user_data["full_name"],
                        role=user_data["role"],
                        password_hash=password_hash,
                        is_active=True
                    )

                    session.add(user)

                    logger.info(
                        f"✅ Added user object: "
                        f"{user_data['username']}"
                    )
                logger.info("💾 Committing transaction...")
                await session.commit()
                logger.info("🎉 Demo users seeded successfully")
            except Exception as e:
                logger.exception(
                    "❌ Demo user seeding failed"
                )
                await session.rollback()
                raise
        
    def _hash_password(self, password: str) -> str:
        """Simple password hashing (use proper bcrypt in production)"""
        return hashlib.sha256(f"{password}_finbot_salt".encode()).hexdigest()
    
    async def get_async_session(self) -> AsyncSession:
        """Get async database session"""
        return self.async_session()
    
    async def close(self):
        """Close database connections"""
        await self.async_engine.dispose()
        self.sync_engine.dispose()


# Global database manager instance
db_manager = DatabaseManager()


# Dependency for FastAPI endpoints
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency to get database session"""
    async with db_manager.async_session() as session:
        try:
            yield session
        finally:
            await session.close()