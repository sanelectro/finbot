from pydantic import BaseModel, Field
from typing import List

class ProcessingSettings(BaseModel):
    """Document processing settings"""
    chunk_size: int = Field(default=512, description="Base chunk size for document splitting")
    chunk_overlap: int = Field(default=50, description="Overlap between chunks")
    
    # Supported file extensions
    supported_file_types: List[str] = Field(default=[
        ".pdf", ".docx", ".doc", ".md", ".txt", ".csv", ".xlsx", ".xls",
        ".py", ".yaml", ".yml", ".json", ".html", ".htm"
    ], description="File types supported by the document processor")
