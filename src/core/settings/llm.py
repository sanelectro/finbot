from pydantic import BaseModel, Field
from typing import Optional

class LLMSettings(BaseModel):
    """LLM settings"""
    groq_api_key: Optional[str] = Field(default=None, description="Groq API key", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama-3.1-8b-instant", description="Groq model name")
