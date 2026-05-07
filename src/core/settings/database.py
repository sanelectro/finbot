"""
Database configuration settings for FinBot
"""

from pydantic import Field
from pydantic_settings import BaseSettings


class DatabaseSettings(BaseSettings):
    """Database connection settings"""
    
    # PostgreSQL settings
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5435, description="PostgreSQL port")
    postgres_user: str = Field(default="finbot", description="PostgreSQL username")
    postgres_password: str = Field(default="finbot123", description="PostgreSQL password")
    postgres_database: str = Field(default="finbot_db", description="PostgreSQL database name")
    
    # Connection pool settings
    pool_size: int = Field(default=5, description="Connection pool size")
    max_overflow: int = Field(default=10, description="Max pool overflow")
    pool_timeout: int = Field(default=30, description="Pool connection timeout")
    
    @property
    def database_url(self) -> str:
        """Construct database URL"""
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )
    
    @property
    def async_database_url(self) -> str:
        """Construct async database URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_database}"
        )