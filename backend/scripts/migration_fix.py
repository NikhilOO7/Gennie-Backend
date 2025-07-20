#!/usr/bin/env python3
"""
Fix migration state when tables already exist
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import text
from app.database import engine
import subprocess

# Color codes
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'

async def check_current_state():
    """Check current database state"""
    print(f"{BLUE}Checking current database state...{NC}")
    
    async with engine.connect() as conn:
        # Check if alembic_version table exists
        result = await conn.execute(text("""
            SELECT EXISTS (
                SELECT FROM pg_tables 
                WHERE tablename = 'alembic_version'
            );
        """))
        has_alembic = result.scalar()
        
        # Get list of existing tables
        result = await conn.execute(text("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public' 
            ORDER BY tablename;
        """))
        tables = [row[0] for row in result]
        
        # Get current alembic version if exists
        current_version = None
        if has_alembic:
            result = await conn.execute(text("SELECT version_num FROM alembic_version"))
            row = result.first()
            if row:
                current_version = row[0]
    
    return {
        'has_alembic': has_alembic,
        'tables': tables,
        'current_version': current_version
    }

async def fix_migration_state():
    """Fix the migration state"""
    state = await check_current_state()
    
    print(f"\n{YELLOW}Current state:{NC}")
    print(f"  Alembic tracking: {'Yes' if state['has_alembic'] else 'No'}")
    print(f"  Current version: {state['current_version'] or 'None'}")
    print(f"  Existing tables: {', '.join(state['tables'])}")
    
    # Since tables exist but migration is trying to drop non-existent column
    print(f"\n{YELLOW}The migration is out of sync with the database.{NC}")
    print("Choose an option:")
    print("1. Mark current state as up-to-date (recommended)")
    print("2. Delete all tables and start fresh (LOSES ALL DATA)")
    print("3. Create a new migration from current state")
    print("4. Cancel")
    
    choice = input("\nEnter choice (1-4): ")
    
    if choice == "1":
        await mark_as_current()
    elif choice == "2":
        await drop_and_recreate()
    elif choice == "3":
        await create_new_migration()
    elif choice == "4":
        print("Cancelled")
    else:
        print("Invalid choice")

async def mark_as_current():
    """Mark current database state as up-to-date"""
    print(f"\n{YELLOW}Marking current state as up-to-date...{NC}")
    
    # Get the latest migration revision
    result = subprocess.run(
        ["alembic", "heads"],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        latest_revision = result.stdout.strip().split()[0]
        print(f"Latest revision: {latest_revision}")
        
        # Stamp the database with this revision
        subprocess.run(["alembic", "stamp", latest_revision])
        
        print(f"{GREEN}✓ Database marked as up-to-date{NC}")
    else:
        print(f"{RED}Failed to get latest revision{NC}")

async def drop_and_recreate():
    """Drop all tables and recreate"""
    print(f"\n{RED}⚠️  WARNING: This will DELETE ALL DATA!{NC}")
    confirm = input("Type 'DELETE ALL' to confirm: ")
    
    if confirm == "DELETE ALL":
        async with engine.begin() as conn:
            # Drop all tables
            await conn.execute(text("DROP SCHEMA public CASCADE;"))
            await conn.execute(text("CREATE SCHEMA public;"))
            print(f"{GREEN}✓ All tables dropped{NC}")
        
        # Remove old migrations
        migrations_dir = Path("alembic/versions")
        for file in migrations_dir.glob("*.py"):
            file.unlink()
        print(f"{GREEN}✓ Old migrations removed{NC}")
        
        # Create new migration
        subprocess.run([
            "alembic", "revision", "--autogenerate", 
            "-m", "initial_schema"
        ])
        
        # Apply migration
        subprocess.run(["alembic", "upgrade", "head"])
        
        print(f"{GREEN}✓ Database recreated with fresh migration{NC}")
    else:
        print("Cancelled")

async def create_new_migration():
    """Create a new migration from current state"""
    print(f"\n{YELLOW}Creating new migration from current state...{NC}")
    
    # First, mark current state
    async with engine.begin() as conn:
        # Ensure alembic_version table exists
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alembic_version (
                version_num VARCHAR(32) NOT NULL,
                CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
            );
        """))
    
    # Remove problematic migration
    problematic_file = Path("alembic/versions/793e27aceba8_initial_schema.py")
    if problematic_file.exists():
        backup_name = f"alembic/versions/backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}_793e27aceba8_initial_schema.py"
        problematic_file.rename(backup_name)
        print(f"{YELLOW}Backed up problematic migration to {backup_name}{NC}")
    
    # Create a migration that represents current state
    # This will likely create an empty migration since tables match models
    result = subprocess.run([
        "alembic", "revision", "--autogenerate",
        "-m", "sync_with_existing_schema"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print(f"{GREEN}✓ Created new migration{NC}")
        
        # Apply it to update alembic_version
        subprocess.run(["alembic", "upgrade", "head"])
        print(f"{GREEN}✓ Migration state synchronized{NC}")
    else:
        print(f"{RED}Failed to create migration: {result.stderr}{NC}")

async def main():
    """Main function"""
    print(f"{BLUE}{'='*60}{NC}")
    print(f"{BLUE}Migration State Fixer{NC}")
    print(f"{BLUE}{'='*60}{NC}")
    
    await fix_migration_state()

if __name__ == "__main__":
    asyncio.run(main())