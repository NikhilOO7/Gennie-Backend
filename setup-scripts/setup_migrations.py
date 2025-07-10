#!/usr/bin/env python3
"""
Migration Setup and Management Script for Gennie Backend
Handles Alembic initialization and provides migration utilities
"""

import os
import sys
from pathlib import Path
import subprocess
from datetime import datetime

# Add parent directory to path to import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Color codes for output
RED = '\033[0;31m'
GREEN = '\033[0;32m'
YELLOW = '\033[1;33m'
BLUE = '\033[0;34m'
NC = '\033[0m'  # No Color

# Get project root directory (parent of setup-scripts)
PROJECT_ROOT = Path(__file__).parent.parent


def run_command(cmd, capture_output=False, cwd=None):
    """Run a shell command and handle errors"""
    if cwd is None:
        cwd = PROJECT_ROOT
    
    print(f"{BLUE}Running: {cmd}{NC}")
    try:
        if capture_output:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=cwd)
            return result.stdout.strip()
        else:
            subprocess.run(cmd, shell=True, check=True, cwd=cwd)
            return True
    except subprocess.CalledProcessError as e:
        print(f"{RED}Error running command: {e}{NC}")
        return False if not capture_output else ""


def setup_alembic():
    """Initialize Alembic if not already set up"""
    alembic_ini = PROJECT_ROOT / "alembic.ini"
    
    if not alembic_ini.exists():
        print(f"{YELLOW}Setting up Alembic...{NC}")
        run_command("alembic init alembic")
        
        # Update alembic.ini with correct database URL
        print(f"{YELLOW}Configuring alembic.ini...{NC}")
        with open(alembic_ini, "r") as f:
            content = f.read()
        
        # Update the sqlalchemy.url line to use environment variable
        content = content.replace(
            "sqlalchemy.url = driver://user:pass@localhost/dbname",
            "sqlalchemy.url = postgresql://chatbot_user:GmwemWrdiJGdtLz697sFAJsvl@localhost/chatbot_db"
        )
        
        with open(alembic_ini, "w") as f:
            f.write(content)
        
        # Update alembic/env.py to import models
        env_py = PROJECT_ROOT / "alembic" / "env.py"
        with open(env_py, "r") as f:
            env_content = f.read()
        
        # Add imports at the beginning
        imports = """import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models import *
from app.database import Base
from app.config import settings
"""
        
        # Insert imports after the initial comments
        import_pos = env_content.find("from alembic import context")
        env_content = env_content[:import_pos] + imports + "\n" + env_content[import_pos:]
        
        # Update target_metadata
        env_content = env_content.replace(
            "target_metadata = None",
            "target_metadata = Base.metadata"
        )
        
        with open(env_py, "w") as f:
            f.write(env_content)
        
        print(f"{GREEN}✓ Alembic initialized{NC}")
    else:
        print(f"{GREEN}✓ Alembic already initialized{NC}")


def create_migration(message):
    """Create a new migration"""
    if not message:
        print(f"{RED}Error: Migration message is required{NC}")
        return False
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_message = message.replace(" ", "_").lower()
    
    print(f"{YELLOW}Creating migration: {message}{NC}")
    return run_command(f'alembic revision --autogenerate -m "{safe_message}"')


def run_migrations():
    """Apply all pending migrations"""
    print(f"{YELLOW}Applying migrations...{NC}")
    return run_command("alembic upgrade head")


def rollback_migration(steps=1):
    """Rollback migrations by specified number of steps"""
    print(f"{YELLOW}Rolling back {steps} migration(s)...{NC}")
    return run_command(f"alembic downgrade -{steps}")


def show_migration_status():
    """Show current migration status"""
    print(f"{YELLOW}Current migration status:{NC}")
    run_command("alembic current")
    print(f"\n{YELLOW}Migration history:{NC}")
    run_command("alembic history")


def reset_database():
    """Reset database to initial state (DANGEROUS!)"""
    print(f"{RED}⚠️  WARNING: This will delete all data!{NC}")
    response = input("Are you sure you want to reset the database? (yes/no): ")
    
    if response.lower() == "yes":
        print(f"{YELLOW}Resetting database...{NC}")
        run_command("alembic downgrade base")
        run_command("alembic upgrade head")
        print(f"{GREEN}✓ Database reset complete{NC}")
    else:
        print("Database reset cancelled")


def create_migration_scripts():
    """Create helper scripts for migration management"""
    
    scripts_dir = PROJECT_ROOT / "scripts"
    scripts_dir.mkdir(exist_ok=True)
    
    # Create migrate.sh in scripts directory
    migrate_script = scripts_dir / "migrate.sh"
    with open(migrate_script, "w") as f:
        f.write("""#!/bin/bash
# Quick migration script

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

cd "$PROJECT_ROOT"

case "$1" in
    "create")
        if [ -z "$2" ]; then
            echo "Usage: ./scripts/migrate.sh create 'migration message'"
            exit 1
        fi
        python setup-scripts/setup_migrations.py create "$2"
        ;;
    "up")
        python setup-scripts/setup_migrations.py up
        ;;
    "down")
        python setup-scripts/setup_migrations.py down ${2:-1}
        ;;
    "status")
        python setup-scripts/setup_migrations.py status
        ;;
    "reset")
        python setup-scripts/setup_migrations.py reset
        ;;
    *)
        echo "Usage: ./scripts/migrate.sh {create|up|down|status|reset}"
        echo "  create 'message' - Create new migration"
        echo "  up              - Apply all migrations"
        echo "  down [n]        - Rollback n migrations (default: 1)"
        echo "  status          - Show migration status"
        echo "  reset           - Reset database (DANGEROUS!)"
        exit 1
        ;;
esac
""")
    os.chmod(migrate_script, 0o755)
    print(f"{GREEN}✓ Created {migrate_script}{NC}")


def main():
    """Main function to handle command line arguments"""
    if len(sys.argv) < 2:
        print(f"""
{YELLOW}Gennie Backend Migration Manager{NC}

Usage: python setup_migrations.py [command] [options]

Commands:
  init              Initialize Alembic
  create 'message'  Create a new migration
  up               Apply all pending migrations
  down [n]         Rollback n migrations (default: 1)
  status           Show migration status
  reset            Reset database (DANGEROUS!)
  setup            Set up migration scripts

Example:
  python setup_migrations.py create "add user preferences table"
  python setup_migrations.py up
""")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "init":
        setup_alembic()
    
    elif command == "create":
        if len(sys.argv) < 3:
            print(f"{RED}Error: Migration message required{NC}")
            sys.exit(1)
        create_migration(sys.argv[2])
    
    elif command == "up":
        run_migrations()
    
    elif command == "down":
        steps = int(sys.argv[2]) if len(sys.argv) > 2 else 1
        rollback_migration(steps)
    
    elif command == "status":
        show_migration_status()
    
    elif command == "reset":
        reset_database()
    
    elif command == "setup":
        setup_alembic()
        create_migration_scripts()
        print(f"\n{GREEN}✓ Migration setup complete!{NC}")
        print(f"\n{YELLOW}You can now use:{NC}")
        print(f"  cd .. # Go to project root")
        print(f"  ./scripts/migrate.sh create 'migration message'")
        print(f"  ./scripts/migrate.sh up")
        print(f"  ./scripts/migrate.sh status")
    
    else:
        print(f"{RED}Unknown command: {command}{NC}")
        sys.exit(1)


if __name__ == "__main__":
    main()