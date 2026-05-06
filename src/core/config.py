"""
Configuration settings for FinBot
"""

from pydantic_settings import BaseSettings

from src.core.settings.data import DataSettings
from src.core.settings.vector_store import VectorStoreSettings
from src.core.settings.embeddings import EmbeddingsSettings
from src.core.settings.llm import LLMSettings
from src.core.settings.processing import ProcessingSettings
from src.core.settings.rbac import RBACSettings
from src.core.settings.api import APISettings

class Settings(
    DataSettings,
    VectorStoreSettings,
    EmbeddingsSettings,
    LLMSettings,
    ProcessingSettings,
    RBACSettings,
    APISettings,
    BaseSettings
):
    """FinBot application settings"""
    
    class Config:
        env_prefix = "FINBOT_"
        env_file = [".env", "local.env"]  # Try both .env and local.env
        env_file_encoding = 'utf-8'

# Global settings instance
settings = Settings()
