from pydantic import BaseModel, Field
from pathlib import Path

class DataSettings(BaseModel):
    """Data and storage settings"""
    data_dir: Path = Field(default=Path("data"), description="Directory containing document collections")
