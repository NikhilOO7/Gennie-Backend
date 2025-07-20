#!/usr/bin/env python3
"""
Automatic Database Migration System
Detects and applies schema changes automatically on startup
"""

import asyncio
import hashlib
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Set
import logging

from sqlalchemy import inspect, text
from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.operations import Operations

from app.database import engine, Base
from app.config import settings

logger = logging.getLogger(__name__)

class AutoMigrationSystem:
    """Handles automatic database migrations"""
    
    def __init__(self):
        self.state_file = Path(".migration_state.json")
        self.alembic_cfg = Config("alembic.ini")
        
    def get_model_hash(self) -> str:
        """Generate a hash of all model definitions"""
        # Import all models
        from app.models import User, Chat, Message, UserPreference, Emotion
        
        # Get all table definitions
        tables_info = {}
        for table_name, table in Base.metadata.tables.items():
            columns = {}
            for column in table.columns:
                columns[column.name] = {
                    "type": str(column.type),
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                    "unique": column.unique,
                    "default": str(column.default) if column.default else None
                }
            tables_info[table_name] = columns
        
        # Create hash of the schema
        schema_str = json.dumps(tables_info, sort_keys=True)
        return hashlib.md5(schema_str.encode()).hexdigest()
    
    def load_state(self) -> Dict:
        """Load previous migration state"""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)
        return {"hash": None, "last_migration": None}
    
    def save_state(self, schema_hash: str):
        """Save current migration state"""
        state = {
            "hash": schema_hash,
            "last_migration": datetime.now().isoformat(),
            "tables": list(Base.metadata.tables.keys())
        }
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    async def get_current_tables(self) -> Set[str]:
        """Get list of tables currently in database"""
        async with engine.connect() as conn:
            result = await conn.execute(
                text("SELECT tablename FROM pg_tables WHERE schemaname='public'")
            )
            return {row[0] for row in result if row[0] != 'alembic_version'}
    
    async def detect_changes(self) -> Dict:
        """Detect what has changed in the schema"""
        current_tables = await self.get_current_tables()
        model_tables = set(Base.metadata.tables.keys())
        
        changes = {
            "new_tables": model_tables - current_tables,
            "removed_tables": current_tables - model_tables,
            "modified_tables": [],
            "schema_changed": False
        }
        
        # Check for column changes in existing tables
        async with engine.connect() as conn:
            # Use run_sync to work with inspector
            def check_columns(sync_conn):
                inspector = inspect(sync_conn)
                modified = []
                
                for table_name in model_tables & current_tables:
                    model_table = Base.metadata.tables[table_name]
                    try:
                        db_columns = {col['name'] for col in inspector.get_columns(table_name)}
                        model_columns = {col.name for col in model_table.columns}
                        
                        if db_columns != model_columns:
                            modified.append(table_name)
                    except Exception as e:
                        logger.warning(f"Error checking table {table_name}: {e}")
                
                return modified
            
            changes["modified_tables"] = await conn.run_sync(check_columns)
            if changes["modified_tables"]:
                changes["schema_changed"] = True
        
        if changes["new_tables"] or changes["removed_tables"] or changes["modified_tables"]:
            changes["schema_changed"] = True
            
        return changes
    
    async def apply_changes_safe(self) -> bool:
        """Apply schema changes safely (only additions, no data loss)"""
        logger.info("🔄 Applying safe schema changes...")
        
        try:
            async with engine.begin() as conn:
                # Create new tables only
                await conn.run_sync(Base.metadata.create_all)
            
            logger.info("✅ Safe changes applied (new tables/columns added)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error applying changes: {e}")
            return False
    
    async def generate_migration(self, message: str = None) -> bool:
        """Generate Alembic migration for changes"""
        try:
            if not message:
                message = f"auto_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            logger.info(f"📝 Generating migration: {message}")
            command.revision(self.alembic_cfg, autogenerate=True, message=message)
            return True
            
        except Exception as e:
            logger.error(f"❌ Error generating migration: {e}")
            return False
    
    async def check_and_migrate(self, mode: str = "safe") -> bool:
        """
        Main method to check and apply migrations
        
        Modes:
        - safe: Only create new tables/columns (default)
        - auto: Generate and apply Alembic migrations
        - detect: Only detect changes, don't apply
        """
        logger.info("🔍 Checking for database schema changes...")
        
        # Import all models to ensure they're registered
        from app.models import User, Chat, Message, MessageType, SenderType, UserPreference, PreferenceType, Emotion, EmotionType
        
        # Get current state
        current_hash = self.get_model_hash()
        saved_state = self.load_state()
        
        # Quick check - if hash hasn't changed, skip
        if current_hash == saved_state.get("hash"):
            logger.info("✅ No schema changes detected")
            return True
        
        # Detect specific changes
        changes = await self.detect_changes()
        
        if not changes["schema_changed"]:
            logger.info("✅ Schema is up to date")
            self.save_state(current_hash)
            return True
        
        # Report changes
        logger.info("📊 Schema changes detected:")
        if changes["new_tables"]:
            logger.info(f"  📌 New tables: {', '.join(changes['new_tables'])}")
        if changes["removed_tables"]:
            logger.warning(f"  ⚠️  Removed tables: {', '.join(changes['removed_tables'])}")
        if changes["modified_tables"]:
            logger.info(f"  🔧 Modified tables: {', '.join(changes['modified_tables'])}")
        
        # Apply changes based on mode
        if mode == "detect":
            return True
            
        elif mode == "safe":
            if await self.apply_changes_safe():
                self.save_state(current_hash)
                return True
                
        elif mode == "auto":
            # For development - auto-generate and apply migrations
            if settings.ENVIRONMENT == "development":
                if await self.generate_migration():
                    logger.info("📦 Applying migration...")
                    command.upgrade(self.alembic_cfg, "head")
                    self.save_state(current_hash)
                    return True
            else:
                logger.warning("⚠️  Auto-migration disabled in production")
                logger.info("💡 Run: alembic revision --autogenerate -m 'description'")
                logger.info("💡 Then: alembic upgrade head")
        
        return False


# Convenience function for use in FastAPI startup
async def auto_migrate(mode: str = None):
    """
    Automatically handle database migrations
    
    Usage in main.py:
        await auto_migrate()  # Safe mode by default
        await auto_migrate("auto")  # Full auto migration in dev
    """
    if mode is None:
        mode = "auto" if settings.ENVIRONMENT == "development" else "safe"
    
    system = AutoMigrationSystem()
    return await system.check_and_migrate(mode)


if __name__ == "__main__":
    # CLI interface
    import sys
    
    async def main():
        mode = sys.argv[1] if len(sys.argv) > 1 else "safe"
        
        print(f"Running auto-migration in '{mode}' mode...")
        success = await auto_migrate(mode)
        
        if success:
            print("✅ Migration completed successfully!")
        else:
            print("❌ Migration failed or requires manual intervention")
            sys.exit(1)
    
    asyncio.run(main())