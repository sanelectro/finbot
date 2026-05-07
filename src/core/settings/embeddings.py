from pydantic import BaseModel, Field

class EmbeddingsSettings(BaseModel):
    """Embedding settings"""
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="Sentence transformer model")
    semantic_router_model: str = Field(default="Qwen/Qwen3-Embedding-0.6B", description="Semantic router embedding model")
    embedding_dimension: int = Field(default=384, description="Embedding vector dimension")
