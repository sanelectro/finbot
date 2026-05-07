"""
User CRUD API endpoints for FinBot
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError
from pydantic import BaseModel, EmailStr, Field
import logging
import hashlib
from datetime import datetime

from src.core.database import get_db_session
from src.models.database import User, UserRole

logger = logging.getLogger(__name__)

# Create the users router
router = APIRouter()

# Request/Response models
class UserCreate(BaseModel):
    """User creation request model"""
    username: str = Field(..., min_length=3, max_length=50, description="Unique username")
    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=2, max_length=100, description="Full name")
    role: UserRole = Field(..., description="User role for RBAC")
    is_active: bool = Field(default=True, description="Whether user is active")


class UserUpdate(BaseModel):
    """User update request model"""
    email: Optional[EmailStr] = Field(None, description="User email address")
    full_name: Optional[str] = Field(None, min_length=2, max_length=100, description="Full name")
    role: Optional[UserRole] = Field(None, description="User role for RBAC")
    is_active: Optional[bool] = Field(None, description="Whether user is active")


class UserResponse(BaseModel):
    """User response model"""
    id: int
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Users list response"""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


def _hash_password(password: str) -> str:
    """Simple password hashing (use proper bcrypt in production)"""
    return hashlib.sha256(f"{password}_finbot_salt".encode()).hexdigest()


@router.get("/users", response_model=UserListResponse)
async def get_users(
    page: int = 1,
    page_size: int = 20,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_db_session)
):
    """
    Get all users with optional filtering and pagination.
    
    - **page**: Page number (1-based)
    - **page_size**: Number of users per page (max 100)
    - **role**: Filter by user role
    - **is_active**: Filter by active status
    """
    try:
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(status_code=400, detail="Page must be >= 1")
        if page_size < 1 or page_size > 100:
            raise HTTPException(status_code=400, detail="Page size must be between 1 and 100")
        
        # Build query
        query = select(User)
        
        # Apply filters
        if role is not None:
            # Compare against enum string value to match database storage
            query = query.where(User.role == role.value)
        if is_active is not None:
            query = query.where(User.is_active == is_active)
        
        # Get total count
        count_query = select(func.count()).select_from(User)
        if role is not None:
            # Use same comparison method for consistency
            count_query = count_query.where(User.role == role.value)
        if is_active is not None:
            count_query = count_query.where(User.is_active == is_active)
        
        total_result = await db.execute(count_query)
        total = total_result.scalar() or 0
        
        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        # Execute query
        result = await db.execute(query)
        users = result.scalars().all()
        
        return UserListResponse(
            users=[UserResponse.model_validate(user) for user in users],
            total=total,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        logger.error(f"Error fetching users: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch users")


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: AsyncSession = Depends(get_db_session)):
    """Get user by ID"""
    try:
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        return UserResponse.model_validate(user)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch user")


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, db: AsyncSession = Depends(get_db_session)):
    """
    Create a new user with demo123 password.
    
    All users are created with password 'demo123' for demo purposes.
    """
    try:
        # Hash the default demo password
        password_hash = _hash_password("demo123")
        
        # Create new user
        user = User(
            username=user_data.username,
            email=user_data.email,
            full_name=user_data.full_name,
            role=user_data.role,
            password_hash=password_hash,
            is_active=user_data.is_active
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Created new user: {user.username} with role {user.role.value}")
        
        return UserResponse.model_validate(user)
        
    except IntegrityError as e:
        await db.rollback()
        if "username" in str(e):
            raise HTTPException(status_code=400, detail="Username already exists")
        elif "email" in str(e):
            raise HTTPException(status_code=400, detail="Email already exists")
        else:
            raise HTTPException(status_code=400, detail="User creation failed due to constraint violation")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating user: {e}")
        raise HTTPException(status_code=500, detail="Failed to create user")


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    db: AsyncSession = Depends(get_db_session)
):
    """Update user by ID"""
    try:
        # Check if user exists
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Update fields
        update_data = user_data.dict(exclude_unset=True)
        if update_data:
            for field, value in update_data.items():
                setattr(user, field, value)
            
            await db.commit()
            await db.refresh(user)
            
            logger.info(f"Updated user: {user.username}")
        
        return UserResponse.model_validate(user)
        
    except HTTPException:
        raise
    except IntegrityError as e:
        await db.rollback()
        if "email" in str(e):
            raise HTTPException(status_code=400, detail="Email already exists")
        else:
            raise HTTPException(status_code=400, detail="User update failed due to constraint violation")
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update user")


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, db: AsyncSession = Depends(get_db_session)):
    """Delete user by ID"""
    try:
        # Check if user exists
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Delete user
        await db.delete(user)
        await db.commit()
        
        logger.info(f"Deleted user: {user.username} (ID: {user_id})")
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete user")


@router.post("/users/{user_id}/reset-password", response_model=UserResponse)
async def reset_password(user_id: int, db: AsyncSession = Depends(get_db_session)):
    """
    Reset user password to default 'demo123'
    """
    try:
        # Check if user exists
        user = await db.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Reset to demo password
        new_password_hash = _hash_password("demo123")
        setattr(user, 'password_hash', new_password_hash)
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"Reset password for user: {user.username}")
        
        return UserResponse.model_validate(user)
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error resetting password for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset password")