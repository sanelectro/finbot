from pydantic import BaseModel, Field

class APISettings(BaseModel):
    """API settings"""
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
