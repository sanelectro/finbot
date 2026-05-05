"""
Configuration settings for FinBot
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path
from typing import Dict, List, Optional
import os

class Settings(BaseSettings):
    """FinBot application settings"""
    
    # Data and storage settings
    data_dir: Path = Field(default=Path("data"), description="Directory containing document collections")
    
    # Vector store settings
    qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant server URL")
    qdrant_api_key: Optional[str] = Field(default=None, description="Qdrant API key")
    collection_name: str = Field(default="finbot_documents", description="Qdrant collection name")
    
    # Embedding settings
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="Sentence transformer model")
    embedding_dimension: int = Field(default=384, description="Embedding vector dimension")
    
    # Document processing settings
    chunk_size: int = Field(default=512, description="Base chunk size for document splitting")
    chunk_overlap: int = Field(default=50, description="Overlap between chunks")
    
    # RBAC settings - Role to document collection access mapping
    role_access_matrix: Dict[str, List[str]] = Field(default={
        "employee": ["general"],
        "finance": ["general", "finance"], 
        "engineering": ["general", "engineering"],
        "marketing": ["general", "marketing"],
        "c_level": ["general", "finance", "engineering", "marketing"]
    })
    
    # Collection to access roles mapping (inverse of role_access_matrix)
    @property
    def collection_access_roles(self) -> Dict[str, List[str]]:
        """Get which roles can access each collection"""
        access_map = {}
        for role, collections in self.role_access_matrix.items():
            for collection in collections:
                if collection not in access_map:
                    access_map[collection] = []
                access_map[collection].append(role)
        return access_map
    
    # Supported file extensions by collection
    collection_file_types: Dict[str, List[str]] = Field(default={
        "general": [".pdf", ".md", ".txt"],
        "finance": [".pdf", ".docx", ".doc"],
        "engineering": [".md", ".txt", ".py", ".yaml", ".yml"],
        "marketing": [".pdf", ".docx", ".doc"]
    })
    
    # API settings
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
    
    class Config:
        env_prefix = "FINBOT_"
        env_file = ".env"

# Global settings instance
settings = Settings()