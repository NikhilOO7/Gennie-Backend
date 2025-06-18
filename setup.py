#!/usr/bin/env python3
"""
Chat Backend - Master Setup Script
Handles all setup operations for different environments
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

class ChatBackendSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.setup_dir = self.project_root / "setup"
        
    def setup_development(self):
        """Setup development environment"""
        print("🚀 Setting up development environment...")
        
        # Install dependencies
        print("📦 Installing dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        subprocess.run([sys.executable, "-m", "pip", "install", "pytest", "pytest-asyncio", "black", "isort"])
        
        # Start development services
        print("🐳 Starting development services...")
        subprocess.run(["docker-compose", "up", "-d"])
        
        # Run database migrations
        print("🗄️ Running database migrations...")
        subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"])
        
        print("✅ Development environment ready!")
        print("🌐 API will be available at: http://localhost:8000")
        print("📚 API docs at: http://localhost:8000/docs")
    
    def setup_production(self):
        """Setup production environment"""
        print("🚀 Setting up production environment...")
        
        # Install production dependencies only
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        
        # Build production containers
        print("🐳 Building production containers...")
        subprocess.run(["docker-compose", "-f", "docker-compose.yml", "build"])
        
        print("✅ Production environment ready!")
    
    def run_tests(self):
        """Run test suite"""
        print("🧪 Running tests...")
        subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"])
    
    def start_server(self, env="dev"):
        """Start the application server"""
        if env == "dev":
            print("🚀 Starting development server...")
            subprocess.run([
                sys.executable, "-m", "uvicorn", 
                "app.main:app", 
                "--reload", 
                "--host", "0.0.0.0", 
                "--port", "8000"
            ])
        else:
            print("🚀 Starting production server...")
            subprocess.run([
                sys.executable, "-m", "uvicorn", 
                "app.main:app", 
                "--host", "0.0.0.0", 
                "--port", "8000",
                "--workers", "4"
            ])
    
    def clean_project(self):
        """Clean project artifacts"""
        print("🧹 Cleaning project...")
        
        # Remove cache directories
        for cache_dir in self.project_root.rglob("__pycache__"):
            subprocess.run(["rm", "-rf", str(cache_dir)])
        
        for cache_dir in self.project_root.rglob(".pytest_cache"):
            subprocess.run(["rm", "-rf", str(cache_dir)])
        
        # Remove .pyc files
        for pyc_file in self.project_root.rglob("*.pyc"):
            pyc_file.unlink(missing_ok=True)
        
        print("✅ Project cleaned!")

def main():
    parser = argparse.ArgumentParser(description="Chat Backend Setup Script")
    parser.add_argument("command", choices=["setup", "start", "test", "clean"], 
                       help="Command to execute")
    parser.add_argument("--env", choices=["dev", "prod"], default="dev",
                       help="Environment type")
    
    args = parser.parse_args()
    setup = ChatBackendSetup()
    
    if args.command == "setup":
        if args.env == "dev":
            setup.setup_development()
        else:
            setup.setup_production()
    elif args.command == "start":
        setup.start_server(args.env)
    elif args.command == "test":
        setup.run_tests()
    elif args.command == "clean":
        setup.clean_project()

if __name__ == "__main__":
    main()
