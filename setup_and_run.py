#!/usr/bin/env python3
"""
AI Chatbot Backend - Setup and Run Script
Comprehensive script to setup and run the entire project
"""

import os
import sys
import subprocess
import time
import requests
import asyncio
import json
import shutil
from pathlib import Path
from datetime import datetime
import signal
import atexit

# Colors for output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'  # No Color

def print_status(message, color=Colors.GREEN):
    """Print status message with color and timestamp"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{color}[{timestamp}] ✅ {message}{Colors.NC}")

def print_error(message):
    """Print error message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.RED}[{timestamp}] ❌ {message}{Colors.NC}")

def print_warning(message):
    """Print warning message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.YELLOW}[{timestamp}] ⚠️  {message}{Colors.NC}")

def print_info(message):
    """Print info message"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"{Colors.BLUE}[{timestamp}] ℹ️  {message}{Colors.NC}")

def print_header(message):
    """Print section header"""
    print(f"\n{Colors.CYAN}{'='*60}")
    print(f"🚀 {message}")
    print(f"{'='*60}{Colors.NC}")

class ChatbotSetup:
    def __init__(self):
        self.project_root = Path.cwd()
        self.processes = []
        self.setup_signal_handlers()
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        signal.signal(signal.SIGINT, self.cleanup_and_exit)
        signal.signal(signal.SIGTERM, self.cleanup_and_exit)
        atexit.register(self.cleanup)
    
    def cleanup_and_exit(self, signum, frame):
        """Handle interrupt signals"""
        print_warning("Received interrupt signal. Cleaning up...")
        self.cleanup()
        sys.exit(0)
    
    def cleanup(self):
        """Cleanup all spawned processes"""
        for process in self.processes:
            try:
                if process.poll() is None:  # Process still running
                    process.terminate()
                    process.wait(timeout=5)
            except:
                pass

    def run_command(self, command, cwd=None, capture_output=False, check=True):
        """Run a command and return result"""
        try:
            if isinstance(command, str):
                command = command.split()
            
            result = subprocess.run(
                command,
                cwd=cwd or self.project_root,
                capture_output=capture_output,
                text=True,
                check=check
            )
            return result
        except subprocess.CalledProcessError as e:
            if capture_output:
                print_error(f"Command failed: {' '.join(command)}")
                print_error(f"Error: {e.stderr}")
            raise
        except FileNotFoundError:
            print_error(f"Command not found: {command[0]}")
            raise

    def check_prerequisites(self):
        """Check if required tools are installed"""
        print_header("CHECKING PREREQUISITES")
        
        required_tools = {
            'python3': 'Python 3.11+',
            'pip': 'Python package manager',
            'docker': 'Docker container runtime',
            'docker-compose': 'Docker Compose'
        }
        
        missing_tools = []
        
        for tool, description in required_tools.items():
            try:
                result = self.run_command([tool, '--version'], capture_output=True)
                print_status(f"{description}: Found")
            except (subprocess.CalledProcessError, FileNotFoundError):
                print_error(f"{description}: Not found")
                missing_tools.append(tool)
        
        if missing_tools:
            print_error("Missing required tools. Please install:")
            for tool in missing_tools:
                print_error(f"  - {tool}")
            return False
        
        print_status("All prerequisites satisfied")
        return True

    def setup_environment(self):
        """Setup environment file and virtual environment"""
        print_header("SETTING UP ENVIRONMENT")
        
        # Setup .env file
        env_file = self.project_root / ".env"
        env_template = self.project_root / "env file.txt"
        
        if not env_file.exists() and env_template.exists():
            shutil.copy(env_template, env_file)
            print_status("Created .env file from template")
        elif not env_file.exists():
            print_warning(".env file not found, creating basic one...")
            self.create_basic_env_file()
        else:
            print_status(".env file already exists")
        
        # Check for OpenAI API key
        if env_file.exists():
            with open(env_file, 'r') as f:
                env_content = f.read()
                if 'OPENAI_API_KEY=mykey' in env_content or 'OPENAI_API_KEY=' in env_content:
                    print_warning("Please update OPENAI_API_KEY in .env file with your actual API key")
        
        # Setup virtual environment
        venv_path = self.project_root / "venv"
        if not venv_path.exists():
            print_info("Creating virtual environment...")
            self.run_command([sys.executable, '-m', 'venv', 'venv'])
            print_status("Virtual environment created")
        else:
            print_status("Virtual environment already exists")
        
        # Install dependencies
        print_info("Installing Python dependencies...")
        pip_path = self.get_pip_path()
        self.run_command([pip_path, 'install', '--upgrade', 'pip'])
        self.run_command([pip_path, 'install', '-r', 'requirements.txt'])
        print_status("Python dependencies installed")

    def create_basic_env_file(self):
        """Create a basic .env file"""
        env_content = """# AI Chatbot Backend Configuration
APP_NAME=AI Chatbot Backend
APP_VERSION=2.0.0
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG

# Server Settings
HOST=0.0.0.0
PORT=8000
RELOAD=true

# Security Settings (CHANGE IN PRODUCTION!)
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Database Settings
DATABASE_URL=postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_db
POSTGRES_USER=chatbot_user
POSTGRES_PASSWORD=chatbot_password
POSTGRES_DB=chatbot_db

# Redis Settings
REDIS_URL=redis://localhost:6379/0
REDIS_HOST=localhost
REDIS_PORT=6379

# OpenAI Settings (REQUIRED - ADD YOUR KEY!)
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=1000

# CORS Settings
FRONTEND_URL=http://localhost:3000
"""
        with open(".env", "w") as f:
            f.write(env_content)
        print_status("Created basic .env file")

    def get_pip_path(self):
        """Get the correct pip path for the virtual environment"""
        if os.name == 'nt':  # Windows
            return self.project_root / "venv" / "Scripts" / "pip.exe"
        else:  # Unix/Linux/Mac
            return self.project_root / "venv" / "bin" / "pip"

    def get_python_path(self):
        """Get the correct python path for the virtual environment"""
        if os.name == 'nt':  # Windows
            return self.project_root / "venv" / "Scripts" / "python.exe"
        else:  # Unix/Linux/Mac
            return self.project_root / "venv" / "bin" / "python"

    def start_docker_services(self):
        """Start Docker services"""
        print_header("STARTING DOCKER SERVICES")
        
        # Stop any existing services
        try:
            self.run_command(['docker-compose', 'down'], check=False)
        except:
            pass
        
        # Start PostgreSQL and Redis
        print_info("Starting PostgreSQL and Redis...")
        self.run_command(['docker-compose', 'up', '-d', 'postgres', 'redis'])
        
        # Wait for services to be ready
        print_info("Waiting for services to be ready...")
        max_attempts = 30
        
        # Check PostgreSQL
        for attempt in range(max_attempts):
            try:
                result = self.run_command([
                    'docker-compose', 'exec', '-T', 'postgres', 
                    'pg_isready', '-U', 'chatbot_user', '-d', 'chatbot_db'
                ], capture_output=True, check=False)
                if result.returncode == 0:
                    print_status("PostgreSQL is ready")
                    break
            except:
                pass
            
            if attempt < max_attempts - 1:
                print_info(f"Waiting for PostgreSQL... (attempt {attempt + 1}/{max_attempts})")
                time.sleep(2)
        else:
            print_error("PostgreSQL failed to start after 60 seconds")
            return False
        
        # Check Redis
        try:
            result = self.run_command([
                'docker-compose', 'exec', '-T', 'redis', 
                'redis-cli', 'ping'
            ], capture_output=True, check=False)
            if result.returncode == 0:
                print_status("Redis is ready")
            else:
                print_warning("Redis may not be fully ready")
        except:
            print_warning("Could not verify Redis status")
        
        return True

    def run_database_migrations(self):
        """Run database migrations"""
        print_header("RUNNING DATABASE MIGRATIONS")
        
        python_path = self.get_python_path()
        
        try:
            # Check current migration status
            result = self.run_command([python_path, '-m', 'alembic', 'current'], capture_output=True)
            print_info("Current migration status:")
            print(result.stdout)
        except:
            print_warning("Could not check migration status")
        
        # Run migrations
        print_info("Running database migrations...")
        self.run_command([python_path, '-m', 'alembic', 'upgrade', 'head'])
        print_status("Database migrations completed")

    def test_database_connection(self):
        """Test database connection"""
        print_info("Testing database connection...")
        python_path = self.get_python_path()
        
        test_script = '''
import asyncio
import sys
import os
sys.path.insert(0, os.getcwd())

async def test_db():
    try:
        from app.database import check_db_health, check_redis_health
        
        db_healthy = await check_db_health()
        redis_healthy = await check_redis_health()
        
        print(f"Database: {'✅ Healthy' if db_healthy else '❌ Unhealthy'}")
        print(f"Redis: {'✅ Healthy' if redis_healthy else '❌ Unhealthy'}")
        
        return db_healthy and redis_healthy
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_db())
    sys.exit(0 if result else 1)
'''
        
        with open("temp_db_test.py", "w") as f:
            f.write(test_script)
        
        try:
            result = self.run_command([python_path, "temp_db_test.py"], capture_output=True)
            print(result.stdout)
            print_status("Database connection test passed")
            return True
        except subprocess.CalledProcessError:
            print_error("Database connection test failed")
            return False
        finally:
            # Cleanup temp file
            try:
                os.remove("temp_db_test.py")
            except:
                pass

    def start_application(self):
        """Start the FastAPI application"""
        print_header("STARTING APPLICATION")
        
        python_path = self.get_python_path()
        
        print_info("Starting FastAPI application...")
        print_info("Application will be available at:")
        print_info("  📊 API Documentation: http://localhost:8000/docs")
        print_info("  🏥 Health Check: http://localhost:8000/health")
        print_info("  🔍 ReDoc: http://localhost:8000/redoc")
        print_info("")
        print_info("Press Ctrl+C to stop the application")
        print_info("")
        
        try:
            # Start the application
            process = subprocess.Popen([
                python_path, '-m', 'uvicorn', 'app.main:app',
                '--host', '0.0.0.0',
                '--port', '8000',
                '--reload'
            ])
            self.processes.append(process)
            
            # Wait for app to start
            time.sleep(3)
            
            # Test if app is running
            try:
                response = requests.get("http://localhost:8000/health", timeout=5)
                if response.status_code == 200:
                    print_status("Application started successfully!")
                else:
                    print_warning("Application started but health check failed")
            except requests.RequestException:
                print_warning("Application started but not responding to health checks yet")
            
            # Wait for the process
            process.wait()
            
        except KeyboardInterrupt:
            print_warning("Application stopped by user")
        except Exception as e:
            print_error(f"Failed to start application: {e}")

    def verify_setup(self):
        """Verify the complete setup"""
        print_header("VERIFYING SETUP")
        
        checks = [
            ("Environment file", lambda: (self.project_root / ".env").exists()),
            ("Virtual environment", lambda: (self.project_root / "venv").exists()),
            ("Docker services", self.check_docker_services),
            ("Database connection", self.test_database_connection),
        ]
        
        all_passed = True
        for check_name, check_func in checks:
            try:
                if check_func():
                    print_status(f"{check_name}: OK")
                else:
                    print_error(f"{check_name}: FAILED")
                    all_passed = False
            except Exception as e:
                print_error(f"{check_name}: ERROR - {e}")
                all_passed = False
        
        return all_passed

    def check_docker_services(self):
        """Check if Docker services are running"""
        try:
            result = self.run_command(['docker-compose', 'ps'], capture_output=True)
            return 'postgres' in result.stdout and 'redis' in result.stdout
        except:
            return False

    def full_setup(self):
        """Run the complete setup process"""
        print_header("AI CHATBOT BACKEND - FULL SETUP")
        print_info("This script will set up and run your AI Chatbot backend")
        print_info("Make sure Docker is running before proceeding")
        print("")
        
        try:
            # Step 1: Check prerequisites
            if not self.check_prerequisites():
                print_error("Prerequisites check failed. Please install missing tools.")
                return False
            
            # Step 2: Setup environment
            self.setup_environment()
            
            # Step 3: Start Docker services
            if not self.start_docker_services():
                print_error("Failed to start Docker services")
                return False
            
            # Step 4: Run database migrations
            self.run_database_migrations()
            
            # Step 5: Verify setup
            if not self.verify_setup():
                print_error("Setup verification failed")
                return False
            
            print_header("SETUP COMPLETED SUCCESSFULLY")
            print_status("Your AI Chatbot backend is ready!")
            print_info("You can now start the application or run tests")
            print("")
            
            # Ask user if they want to start the app
            response = input(f"{Colors.CYAN}Do you want to start the application now? (y/n): {Colors.NC}")
            if response.lower().startswith('y'):
                self.start_application()
            else:
                print_info("To start the application later, run:")
                print_info("  python setup_and_run.py --start")
            
            return True
            
        except KeyboardInterrupt:
            print_warning("Setup interrupted by user")
            return False
        except Exception as e:
            print_error(f"Setup failed: {e}")
            return False

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI Chatbot Backend Setup and Run Script")
    parser.add_argument("--setup", action="store_true", help="Run full setup")
    parser.add_argument("--start", action="store_true", help="Start the application")
    parser.add_argument("--verify", action="store_true", help="Verify setup")
    parser.add_argument("--docker", action="store_true", help="Start only Docker services")
    parser.add_argument("--migrate", action="store_true", help="Run database migrations")
    
    args = parser.parse_args()
    
    setup = ChatbotSetup()
    
    if args.verify:
        success = setup.verify_setup()
        sys.exit(0 if success else 1)
    elif args.docker:
        success = setup.start_docker_services()
        sys.exit(0 if success else 1)
    elif args.migrate:
        setup.run_database_migrations()
    elif args.start:
        setup.start_application()
    elif args.setup or len(sys.argv) == 1:
        # Run full setup if no args or --setup
        success = setup.full_setup()
        sys.exit(0 if success else 1)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()