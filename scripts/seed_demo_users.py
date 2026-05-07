#!/usr/bin/env python3
"""
Demo Users Seeding Script for FinBot

This script seeds the database with demo users for testing and demonstration.
All users have the password 'demo123' for simplicity.
"""

import asyncio
import sys
import os
import logging

# Add parent directory to path to import from src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.core.database import db_manager
from src.models.database import User, UserRole

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def seed_demo_users():
    """Create demo users with demo123 password"""
    demo_users = [
        {
            "username": "john.employee",
            "email": "john.employee@finsolve.com",
            "full_name": "John Employee",
            "role": UserRole.EMPLOYEE
        },
        {
            "username": "sarah.finance", 
            "email": "sarah.finance@finsolve.com",
            "full_name": "Sarah Finance",
            "role": UserRole.FINANCE
        },
        {
            "username": "mike.engineer",
            "email": "mike.engineer@finsolve.com", 
            "full_name": "Mike Engineer",
            "role": UserRole.ENGINEERING
        },
        {
            "username": "lisa.marketing",
            "email": "lisa.marketing@finsolve.com",
            "full_name": "Lisa Marketing", 
            "role": UserRole.MARKETING
        },
        {
            "username": "robert.hr",
            "email": "robert.hr@finsolve.com",
            "full_name": "Robert HR",
            "role": UserRole.HR
        },
        {
            "username": "maria.ceo",
            "email": "maria.ceo@finsolve.com",
            "full_name": "Maria CEO",
            "role": UserRole.C_LEVEL
        }
    ]
    
    # Hash the demo password (using same method as database.py)
    import hashlib
    password_hash = hashlib.sha256(f"demo123_finbot_salt".encode()).hexdigest()
    
    async with db_manager.async_session() as session:
        try:
            created_count = 0
            skipped_count = 0
            
            for user_data in demo_users:
                # Check if user already exists
                from sqlalchemy import select
                result = await session.execute(
                    select(User).where(User.username == user_data["username"])
                )
                existing_user = result.scalar_one_or_none()
                
                if existing_user:
                    logger.info(f"⏭️  User {user_data['username']} already exists, skipping...")
                    skipped_count += 1
                    continue
                
                # Create new user
                user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    full_name=user_data["full_name"],
                    role=user_data["role"],
                    password_hash=password_hash,
                    is_active=True
                )
                
                session.add(user)
                logger.info(f"✅ Created demo user: {user_data['username']} ({user_data['role'].value})")
                created_count += 1
            
            await session.commit()
            
            logger.info(f"\n🎉 Demo user seeding completed!")
            logger.info(f"📊 Summary:")
            logger.info(f"   - Created: {created_count} users")
            logger.info(f"   - Skipped: {skipped_count} users (already exist)")
            logger.info(f"   - Total: {len(demo_users)} demo users")
            
            if created_count > 0:
                logger.info(f"\n🔑 All demo users have password: demo123")
                logger.info(f"\n📋 Demo User Accounts:")
                for user_data in demo_users:
                    logger.info(f"   - {user_data['username']} ({user_data['role'].value})")
                
        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Failed to seed demo users: {e}")
            raise


async def main():
    """Main function to seed demo users"""
    logger.info("🌱 Starting demo users seeding...")
    
    try:
        # Initialize database tables first (if not already created)
        success = await db_manager.initialize_database()
        if not success:
            logger.error("❌ Failed to initialize database")
            return 1
        
        # Seed demo users
        await seed_demo_users()
        
        logger.info("✅ Demo users seeding script completed successfully!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error during demo users seeding: {e}")
        return 1
    finally:
        # Clean up database connections
        await db_manager.close()


if __name__ == "__main__":
    # Run the seeding script
    exit_code = asyncio.run(main())
    sys.exit(exit_code)