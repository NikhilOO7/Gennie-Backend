#!/usr/bin/env python3
"""
Comprehensive Startup Check Script
Run this before starting the server to ensure everything is properly configured
Fixed with proper SecretStr handling
"""

import sys
import os
import asyncio
import subprocess
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}\n")

def print_status(text, status="✅"):
    print(f"{status} {text}")

def print_error(text):
    print(f"❌ {text}")

def print_warning(text):
    print(f"⚠️  {text}")

def print_info(text):
    print(f"ℹ️  {text}")

def check_environment():
    """Check environment configuration"""
    print_header("CHECKING ENVIRONMENT")
    
    # Check .env file
    env_file = Path(".env")
    if not env_file.exists():
        print_error(".env file not found!")
        print_info("Creating .env from template...")
        
        # Try to copy from env file.txt
        template = Path("env file.txt")
        if template.exists():
            import shutil
            shutil.copy(template, env_file)
            print_status(".env file created from template")
        else:
            print_error("No template found. Please create .env file manually.")
            return False
    else:
        print_status(".env file exists")
    
    # Check critical environment variables
    try:
        from app.config import settings
        
        critical_vars = {
            "DATABASE_URL": settings.DATABASE_URL,
            "REDIS_URL": settings.REDIS_URL,
            "SECRET_KEY": settings.get_secret_key(),  # Fixed: Use getter method
            "OPENAI_API_KEY": settings.get_openai_api_key()  # Fixed: Use getter method
        }
        
        missing = []
        for var, value in critical_vars.items():
            if not value or value == "your-secret-key-here" or value.startswith("sk-your") or value.startswith("your-"):
                missing.append(var)
        
        if missing:
            print_error(f"Missing or invalid environment variables: {', '.join(missing)}")
            print_info("Please update your .env file with valid values")
            return False
        
        print_status("All critical environment variables are set")
        return True
        
    except Exception as e:
        print_error(f"Error checking environment: {str(e)}")
        return False

def check_docker_services():
    """Check if Docker services are running"""
    print_header("CHECKING DOCKER SERVICES")
    
    try:
        # Check if docker is installed
        result = subprocess.run(['docker', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            print_error("Docker is not installed or not in PATH")
            return False
        print_status("Docker is installed")
        
        # Check if docker-compose exists
        compose_file = Path("docker-compose.yml")
        if not compose_file.exists():
            print_error("docker-compose.yml not found")
            return False
        
        # Check if services are running
        result = subprocess.run(['docker-compose', 'ps'], capture_output=True, text=True)
        output = result.stdout
        
        services_running = True
        postgres_running = False
        redis_running = False
        
        # Check each line of output
        for line in output.split('\n'):
            if 'postgres' in line and 'Up' in line:
                postgres_running = True
            if 'redis' in line and 'Up' in line:
                redis_running = True
        
        if not postgres_running:
            print_warning("PostgreSQL container is not running")
            services_running = False
        else:
            print_status("PostgreSQL is running")
            
        if not redis_running:
            print_warning("Redis container is not running")
            services_running = False
        else:
            print_status("Redis is running")
        
        if not services_running:
            print_info("Starting Docker services...")
            subprocess.run(['docker-compose', 'up', '-d', 'postgres', 'redis'])
            print_info("Waiting for services to be ready...")
            import time
            time.sleep(5)  # Give services time to start
            print_status("Docker services started")
        
        return True
        
    except FileNotFoundError:
        print_error("docker-compose command not found")
        return False
    except Exception as e:
        print_error(f"Error checking Docker services: {e}")
        return False

async def check_database():
    """Check database connection and schema"""
    print_header("CHECKING DATABASE")
    
    try:
        from app.database import check_db_health, engine
        from sqlalchemy import inspect, text
        
        # Check basic connection
        healthy = await check_db_health()
        if not healthy:
            print_error("Database connection failed")
            return False
        print_status("Database connection successful")
        
        # Import and run the quick fix script
        print_info("Checking and fixing database schema...")
        try:
            # Import the fix function directly
            sys.path.insert(0, '.')
            from quick_db_fix import fix_database
            
            if fix_database():
                print_status("Database schema is correct")
                return True
            else:
                print_error("Failed to fix database schema")
                return False
        except ImportError:
            print_warning("quick_db_fix.py not found, trying direct schema check...")
            
            # Direct schema check
            from sqlalchemy import create_engine, inspect
            from app.config import settings
            
            sync_db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
            engine = create_engine(sync_db_url)
            
            with engine.connect() as conn:
                inspector = inspect(conn)
                tables = inspector.get_table_names()
                
                if 'chats' in tables:
                    columns = inspector.get_columns('chats')
                    column_names = [col['name'] for col in columns]
                    print_info(f"Found columns in chats table: {', '.join(column_names)}")
                    
                    required_columns = ['chat_metadata', 'context_window_size', 'auto_title_generation', 'session_id']
                    missing = [col for col in required_columns if col not in column_names]
                    
                    if missing:
                        print_error(f"Missing columns: {', '.join(missing)}")
                        print_info("Run quick_db_fix.py to fix the schema")
                        return False
                    else:
                        print_status("All required columns present")
                        return True
                else:
                    print_error("Chats table not found")
                    return False
            
    except Exception as e:
        print_error(f"Database check failed: {e}")
        return False

async def check_redis():
    """Check Redis connection"""
    print_header("CHECKING REDIS")
    
    try:
        from app.database import check_redis_health
        
        healthy = await check_redis_health()
        if healthy:
            print_status("Redis connection successful")
            return True
        else:
            print_error("Redis connection failed")
            return False
            
    except Exception as e:
        print_error(f"Redis check failed: {e}")
        return False

async def run_checks():
    """Run all checks"""
    print_header("GENNIE BACKEND STARTUP CHECK")
    
    all_good = True
    
    # Check environment
    if not check_environment():
        all_good = False
    
    # Check Docker services
    if not check_docker_services():
        all_good = False
    
    # Wait a bit for services to be ready
    if all_good:
        print_info("Waiting for services to be ready...")
        await asyncio.sleep(3)
    
    # Check database
    if not await check_database():
        all_good = False
    
    # Check Redis
    if not await check_redis():
        all_good = False
    
    return all_good

def main():
    """Main function"""
    try:
        # Run all checks
        all_good = asyncio.run(run_checks())
        
        if all_good:
            print_header("✅ ALL CHECKS PASSED")
            print_info("You can now start the server with:")
            print_info("  uvicorn app.main:app --reload")
            print_info("\nOr use the automated script:")
            print_info("  python setup_and_run.py --start")
            return 0
        else:
            print_header("❌ SOME CHECKS FAILED")
            print_info("Please fix the issues above before starting the server")
            print_info("\nTip: If database schema is incorrect, run:")
            print_info("  python quick_db_fix.py")
            return 1
            
    except KeyboardInterrupt:
        print("\n\nStartup check cancelled by user")
        return 1
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())