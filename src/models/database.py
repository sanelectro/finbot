"""
SQLAlchemy database models for FinBot
"""

from sqlalchemy import Column, Integer, String, DateTime, Enum, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from datetime import datetime
import enum

from src.models.document import Role

Base = declarative_base()


class UserRole(enum.Enum):
    """User roles for RBAC"""
    EMPLOYEE = "employee"
    FINANCE = "finance"  
    ENGINEERING = "engineering"
    MARKETING = "marketing"
    HR = "hr"
    C_LEVEL = "c_level"


class User(Base):
    """User model for authentication and RBAC"""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    full_name = Column(String(100), nullable=False)
    password_hash = Column(String(255), nullable=False)  # Will store hashed passwords
    role = Column(Enum(UserRole), nullable=False, default=UserRole.EMPLOYEE)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_login = Column(DateTime(timezone=True), nullable=True)
    
    def __repr__(self):
        return f"<User(username='{self.username}', email='{self.email}', role='{self.role.value}')>"


class Document(Base):
    """Document metadata model"""
    
    __tablename__ = "documents"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    collection = Column(String(50), nullable=False)  # hr, finance, engineering, etc.
    role_access = Column(Enum(UserRole), nullable=False)  # Which role can access this document
    file_size = Column(Integer, nullable=False)  # File size in bytes
    content_type = Column(String(100), nullable=False)  # MIME type
    upload_status = Column(String(20), default="processing", nullable=False)  # processing, completed, failed
    embedding_status = Column(String(20), default="pending", nullable=False)  # pending, processing, completed, failed
    error_message = Column(Text, nullable=True)  # Store any processing errors
    uploaded_by = Column(Integer, nullable=True)  # Reference to user who uploaded
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    def __repr__(self):
        return f"<Document(filename='{self.filename}', collection='{self.collection}', role='{self.role_access.value}')>"