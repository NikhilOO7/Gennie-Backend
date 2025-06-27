#!/usr/bin/env python3
"""
Comprehensive Database Setup and Testing Script
Automatically handles:
- Database schema creation
- Missing columns addition
- Migrations
- Testing
"""

import sys
import os
import asyncio
import subprocess
from pathlib import Path
from datetime import datetime
import logging
from sqlalchemy import text  # ADD THIS IMPORT

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DatabaseSetup:
    """Comprehensive database setup and testing"""
    
    def __init__(self):
        self.project_root = Path.cwd()
        
    def print_header(self, text):
        """Print formatted header"""
        print(f"\n{'='*70}")
        print(f"  {text}")
        print(f"{'='*70}\n")
        
    def print_status(self, text, success=True):
        """Print status message"""
        status = "✅" if success else "❌"
        print(f"{status} {text}")
        
    def print_info(self, text):
        """Print info message"""
        print(f"ℹ️  {text}")
        
    def print_warning(self, text):
        """Print warning message"""
        print(f"⚠️  {text}")
        
    def check_prerequisites(self):
        """Check if all prerequisites are met"""
        self.print_header("CHECKING PREREQUISITES")
        
        # Check Python version
        if sys.version_info < (3, 8):
            self.print_status("Python 3.8+ required", False)
            return False
            
        self.print_status("Python version OK")
        
        # Check if .env exists
        env_file = self.project_root / ".env"
        if not env_file.exists():
            self.print_warning(".env file not found, creating from template...")
            template = self.project_root / "env file.txt"
            if template.exists():
                import shutil
                shutil.copy(template, env_file)
                self.print_status(".env file created")
            else:
                self.print_status(".env file missing", False)
                return False
        else:
            self.print_status(".env file exists")
            
        # Check Docker services
        try:
            result = subprocess.run(
                ['docker-compose', 'ps'], 
                capture_output=True, 
                text=True
            )
            
            if 'postgres' not in result.stdout or 'redis' not in result.stdout:
                self.print_info("Starting Docker services...")
                subprocess.run(['docker-compose', 'up', '-d', 'postgres', 'redis'])
                import time
                time.sleep(5)  # Wait for services
                
            self.print_status("Docker services running")
            
        except FileNotFoundError:
            self.print_status("Docker Compose not found", False)
            return False
            
        return True
        
    def fix_database_schema(self):
        """Fix database schema issues"""
        self.print_header("FIXING DATABASE SCHEMA")
        
        try:
            from app.config import settings
            from sqlalchemy import create_engine, inspect
            from sqlalchemy.exc import SQLAlchemyError
            
            # Use sync database URL
            sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
            
            self.print_info(f"Connecting to database...")
            engine = create_engine(sync_db_url)
            
            with engine.connect() as connection:
                # Start transaction
                trans = connection.begin()
                
                try:
                    inspector = inspect(connection)
                    
                    # Check if tables exist
                    tables = inspector.get_table_names()
                    self.print_info(f"Found tables: {', '.join(tables)}")
                    
                    # Fix chats table
                    if 'chats' in tables:
                        self._fix_chats_table(connection, inspector)
                    else:
                        self.print_warning("Chats table not found, will be created by migrations")
                    
                    # Fix messages table
                    if 'messages' in tables:
                        self._fix_messages_table(connection, inspector)
                    
                    # Fix users table
                    if 'users' in tables:
                        self._fix_users_table(connection, inspector)
                    
                    # Commit changes
                    trans.commit()
                    self.print_status("Database schema fixed successfully")
                    return True
                    
                except Exception as e:
                    trans.rollback()
                    self.print_status(f"Schema fix failed: {str(e)}", False)
                    logger.error(f"Schema fix error: {str(e)}")
                    return False
                    
        except Exception as e:
            self.print_status(f"Database connection failed: {str(e)}", False)
            return False
            
    def _fix_chats_table(self, connection, inspector):
        """Fix chats table schema"""
        columns = inspector.get_columns('chats')
        column_names = [col['name'] for col in columns]
        
        self.print_info(f"Chats table columns: {', '.join(column_names)}")
        
        # Define required columns with their SQL
        required_columns = {
            'chat_metadata': "ALTER TABLE chats ADD COLUMN IF NOT EXISTS chat_metadata JSON DEFAULT '{}' NOT NULL",
            'context_window_size': "ALTER TABLE chats ADD COLUMN IF NOT EXISTS context_window_size INTEGER DEFAULT 10 NOT NULL",
            'auto_title_generation': "ALTER TABLE chats ADD COLUMN IF NOT EXISTS auto_title_generation BOOLEAN DEFAULT true NOT NULL",
            'session_id': "ALTER TABLE chats ADD COLUMN IF NOT EXISTS session_id VARCHAR(36) DEFAULT gen_random_uuid()::text NOT NULL"
        }
        
        # Add missing columns
        for column_name, sql in required_columns.items():
            if column_name not in column_names:
                self.print_info(f"Adding column: {column_name}")
                connection.execute(text(sql))
            else:
                self.print_info(f"Column exists: {column_name}")
                
        # Create indexes
        indexes = inspector.get_indexes('chats')
        index_names = [idx['name'] for idx in indexes]
        
        if 'idx_chat_session' not in index_names:
            self.print_info("Creating session_id index")
            connection.execute(text(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_chat_session ON chats(session_id)"
            ))
            
        # Update existing rows
        connection.execute(text("""
            UPDATE chats 
            SET session_id = gen_random_uuid()::text 
            WHERE session_id IS NULL OR session_id = ''
        """))
        
    def _fix_messages_table(self, connection, inspector):
        """Fix messages table schema"""
        columns = inspector.get_columns('messages')
        column_names = [col['name'] for col in columns]
        
        if 'message_metadata' not in column_names:
            self.print_info("Adding message_metadata column")
            connection.execute(text("""
                ALTER TABLE messages 
                ADD COLUMN IF NOT EXISTS message_metadata JSON DEFAULT '{}' NOT NULL
            """))
            
    def _fix_users_table(self, connection, inspector):
        """Fix users table schema"""
        columns = inspector.get_columns('users')
        column_names = [col['name'] for col in columns]
        
        # Check for password_hash column
        if 'password_hash' not in column_names:
            self.print_info("Adding password_hash column")
            connection.execute(text("""
                ALTER TABLE users 
                ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255) NOT NULL DEFAULT 'temp_hash'
            """))
            
    def run_migrations(self):
        """Run Alembic migrations"""
        self.print_header("RUNNING DATABASE MIGRATIONS")
        
        try:
            # Check current migration status
            self.print_info("Checking migration status...")
            result = subprocess.run(
                ['alembic', 'current'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.print_info(f"Current migration: {result.stdout.strip()}")
            
            # Generate migration if needed
            self.print_info("Checking for schema changes...")
            result = subprocess.run(
                ['alembic', 'revision', '--autogenerate', '-m', 'Auto migration'],
                capture_output=True,
                text=True
            )
            
            if 'No changes' in result.stdout:
                self.print_info("No schema changes detected")
            else:
                self.print_info("Generated new migration")
                
            # Apply migrations
            self.print_info("Applying migrations...")
            result = subprocess.run(
                ['alembic', 'upgrade', 'head'],
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                self.print_status("Migrations applied successfully")
                return True
            else:
                self.print_status(f"Migration failed: {result.stderr}", False)
                return False
                
        except FileNotFoundError:
            self.print_warning("Alembic not found, skipping migrations")
            return True
            
    async def test_database(self):
        """Test database functionality"""
        self.print_header("TESTING DATABASE")
        
        try:
            from app.database import check_db_health, get_db, AsyncSessionLocal
            from app.models.user import User
            from app.models.chat import Chat
            from app.models.message import Message
            from sqlalchemy import select
            
            # Test connection
            if not await check_db_health():
                self.print_status("Database health check failed", False)
                return False
                
            self.print_status("Database connection healthy")
            
            # Test CRUD operations
            async with AsyncSessionLocal() as session:
                try:
                    # Test user creation
                    self.print_info("Testing user creation...")
                    test_user = User(
                        email=f"test_{datetime.now().timestamp()}@example.com",
                        username=f"test_user_{int(datetime.now().timestamp())}",
                        password_hash="dummy_hash",
                        is_active=True
                    )
                    session.add(test_user)
                    await session.commit()
                    await session.refresh(test_user)
                    self.print_status("User creation successful")
                    
                    # Test chat creation
                    self.print_info("Testing chat creation...")
                    test_chat = Chat(
                        user_id=test_user.id,
                        title="Test Chat",
                        chat_metadata={"test": True},
                        context_window_size=10,
                        auto_title_generation=True
                    )
                    session.add(test_chat)
                    await session.commit()
                    await session.refresh(test_chat)
                    self.print_status("Chat creation successful")
                    
                    # Test message creation
                    self.print_info("Testing message creation...")
                    from app.models.message import MessageType, SenderType
                    test_message = Message(
                        chat_id=test_chat.id,
                        content="Test message",
                        message_type=MessageType.TEXT,
                        sender_type=SenderType.USER,
                        message_metadata={"test": True}
                    )
                    session.add(test_message)
                    await session.commit()
                    self.print_status("Message creation successful")
                    
                    # Clean up test data
                    self.print_info("Cleaning up test data...")
                    await session.delete(test_message)
                    await session.delete(test_chat)
                    await session.delete(test_user)
                    await session.commit()
                    self.print_status("Test data cleaned up")
                    
                    return True
                    
                except Exception as e:
                    await session.rollback()
                    self.print_status(f"Database test failed: {str(e)}", False)
                    logger.error(f"Database test error: {str(e)}")
                    return False
                    
        except Exception as e:
            self.print_status(f"Database test setup failed: {str(e)}", False)
            return False
            
    async def run_all(self):
        """Run all setup steps"""
        self.print_header("GENNIE DATABASE SETUP")
        
        # Check prerequisites
        if not self.check_prerequisites():
            return False
            
        # Fix database schema
        if not self.fix_database_schema():
            return False
            
        # Run migrations
        if not self.run_migrations():
            return False
            
        # Test database
        if not await self.test_database():
            return False
            
        return True
        
    def print_summary(self, success):
        """Print setup summary"""
        if success:
            self.print_header("✅ DATABASE SETUP COMPLETE")
            self.print_info("Database is ready for use!")
            self.print_info("\nYou can now start the server with:")
            self.print_info("  uvicorn app.main:app --reload")
            self.print_info("\nOr run the startup check:")
            self.print_info("  python startup_check.py")
        else:
            self.print_header("❌ DATABASE SETUP FAILED")
            self.print_info("Please check the errors above and try again")
            self.print_info("\nFor manual fixes, you can:")
            self.print_info("  1. Check Docker services: docker-compose ps")
            self.print_info("  2. Check logs: docker-compose logs postgres")
            self.print_info("  3. Run quick fix: python quick_db_fix.py")

async def main():
    """Main function"""
    setup = DatabaseSetup()
    
    try:
        success = await setup.run_all()
        setup.print_summary(success)
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n\nSetup cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))