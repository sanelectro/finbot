from pydantic import BaseModel, Field
from typing import Optional

class VectorStoreSettings(BaseModel):
    """Vector store settings"""
    qdrant_url: str = Field(default="http://localhost:6333", description="Qdrant server URL")
    qdrant_api_key: Optional[str] = Field(default=None, description="Qdrant API key")
    collection_name: str = Field(default="finbot_documents", description="Qdrant collection name")
