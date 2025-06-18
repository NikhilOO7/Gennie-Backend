#!/usr/bin/env python3
"""
Chat Backend - Production Cleanup & Restructure Script
Specifically designed for your chat-backend project structure
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path
import json

class ChatBackendCleanup:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root).resolve()
        self.backup_dir = self.project_root / "backup_before_cleanup"
        
        # Files to move to setup directory
        self.setup_files = [
            'check_project.sh',
            'fix_metadata_issue.sh', 
            'project_clean.sh',
            'setup.sh',
            'start.sh',
            'test_config.py',
            'test_day3_features.py',
            'test_installation.py'
        ]
        
        # Directories to move to setup
        self.setup_dirs = [
            'scripts',
            'docs'
        ]
        
        # Files to keep in root (production)
        self.production_files = [
            'LICENSE',
            'README.md',
            'requirements.txt',
            'docker-compose.yml',
            'dockerfile',
            'alembic.ini'  # Will be created if missing
        ]
    
    def create_backup(self):
        """Create backup of current project"""
        print("📦 Creating backup of current project...")
        
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir)
        
        # Copy entire project to backup (excluding .git)
        shutil.copytree(
            self.project_root, 
            self.backup_dir,
            ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc', '.pytest_cache')
        )
        print(f"✅ Backup created at: {self.backup_dir}")
    
    def create_new_structure(self):
        """Create new directory structure"""
        print("🏗️ Creating new directory structure...")
        
        new_dirs = [
            'setup/development',
            'setup/testing', 
            'setup/scripts',
            'setup/documentation',
            'deployment/docker',
            'deployment/scripts',
            'config'
        ]
        
        for dir_path in new_dirs:
            full_path = self.project_root / dir_path
            full_path.mkdir(parents=True, exist_ok=True)
            
            # Create __init__.py for Python packages where appropriate
            if 'setup' in dir_path and not dir_path.endswith('documentation'):
                init_file = full_path / '__init__.py'
                if not init_file.exists():
                    init_file.touch()
        
        print("✅ New directory structure created")
    
    def move_setup_files(self):
        """Move setup and development files"""
        print("📁 Moving setup and development files...")
        
        # Move individual setup files
        for file_name in self.setup_files:
            file_path = self.project_root / file_name
            if file_path.exists():
                if file_name.startswith('test_'):
                    target_dir = self.project_root / 'setup/testing'
                else:
                    target_dir = self.project_root / 'setup/development'
                
                target_dir.mkdir(parents=True, exist_ok=True)
                target_file = target_dir / file_name
                
                shutil.move(str(file_path), str(target_file))
                print(f"  ✓ Moved: {file_name} → setup/{target_dir.name}/")
        
        # Move setup directories
        for dir_name in self.setup_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists():
                if dir_name == 'docs':
                    target_dir = self.project_root / 'setup/documentation'
                else:
                    target_dir = self.project_root / 'setup/scripts'
                
                # Move contents instead of the directory itself
                target_dir.mkdir(parents=True, exist_ok=True)
                
                for item in dir_path.iterdir():
                    target_item = target_dir / item.name
                    shutil.move(str(item), str(target_item))
                
                # Remove empty directory
                dir_path.rmdir()
                print(f"  ✓ Moved: {dir_name}/ → setup/{target_dir.name}/")
    
    def clean_data_directories(self):
        """Clean up data directories"""
        print("🧹 Cleaning data directories...")
        
        data_dir = self.project_root / 'data'
        if data_dir.exists():
            # Move data directory to .gitignore and create empty structure
            postgres_dir = data_dir / 'postgres'
            redis_dir = data_dir / 'redis'
            
            # Remove actual data but keep directory structure
            if postgres_dir.exists():
                shutil.rmtree(postgres_dir)
                postgres_dir.mkdir(exist_ok=True)
                (postgres_dir / '.gitkeep').touch()
            
            if redis_dir.exists():
                shutil.rmtree(redis_dir)  
                redis_dir.mkdir(exist_ok=True)
                (redis_dir / '.gitkeep').touch()
            
            print("  ✓ Cleaned data directories")
    
    def remove_project_structure_md(self):
        """Remove PROJECT_STRUCTURE.md as it will be outdated"""
        print("📄 Removing outdated PROJECT_STRUCTURE.md...")
        
        project_structure_file = self.project_root / 'PROJECT_STRUCTURE.md'
        if project_structure_file.exists():
            project_structure_file.unlink()
            print("  ✓ Removed PROJECT_STRUCTURE.md")
    
    def create_production_configs(self):
        """Create production-ready configuration files"""
        print("⚙️ Creating production configuration files...")
        
        # Create alembic.ini if it doesn't exist
        alembic_ini = self.project_root / 'alembic.ini'
        if not alembic_ini.exists():
            alembic_content = '''# A generic, single database configuration.

[alembic]
# path to migration scripts
script_location = alembic

# template used to generate migration files
file_template = %%(year)d_%%(month).2d_%%(day).2d_%%(hour).2d%%(minute).2d-%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
prepend_sys_path = .

# timezone to use when rendering the date within the migration file
# as well as the filename.
# If specified, requires the python-dateutil library that can be
# installed by adding `alembic[tz]` to the pip requirements
# string value is passed to dateutil.tz.gettz()
# leave blank for localtime
# timezone =

# max length of characters to apply to the
# "slug" field
# truncate_slug_length = 40

# set to 'true' to run the environment during
# the 'revision' command, regardless of autogenerate
# revision_environment = false

# set to 'true' to allow .pyc and .pyo files without
# a source .py file to be detected as revisions in the
# versions/ directory
# sourceless = false

# version number format.  This value is passed to the
# "version_num" argument of env.configure()
# version_num_format = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(second).2d_%%(microsecond).6d

# version number max characters.  This value is passed to the
# "version_num_max_length" argument of env.configure()
# version_num_max_length = 32

# used to identify migration files
version_locations = %(here)s/alembic/versions

# version path separator; As mentioned above, this is the character used to split
# version_locations. The default within new alembic.ini files is "os", which uses
# os.pathsep. If this key is omitted entirely, it falls back to the legacy
# behavior of splitting on spaces followed by semicolons and/or newlines.
version_path_separator = os

# the output encoding used when revision files
# are written from script.py.mako
output_encoding = utf-8

sqlalchemy.url = postgresql://user:password@localhost/dbname

[post_write_hooks]
# post_write_hooks defines scripts or Python functions that are run
# on newly generated revision scripts.

# format using "black" - use the console_scripts runner, against the "black" entrypoint
# hooks = black
# black.type = console_scripts
# black.entrypoint = black
# black.options = -l 79 REVISION_SCRIPT_FILENAME

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
'''
            
            alembic_ini.write_text(alembic_content)
            print("  ✓ Created alembic.ini")
        
        # Create .env.example
        env_example = self.project_root / '.env.example'
        if not env_example.exists():
            env_content = '''# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/chatbot_db
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=chatbot_db

# Redis Configuration  
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here

# Application Configuration
SECRET_KEY=your_secret_key_here
DEBUG=False
ENVIRONMENT=production

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000"]

# JWT Configuration
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
'''
            
            env_example.write_text(env_content)
            print("  ✓ Created .env.example")
        
        # Create pyproject.toml
        pyproject_toml = self.project_root / 'pyproject.toml'
        if not pyproject_toml.exists():
            pyproject_content = '''[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "chat-backend"
version = "1.0.0"
description = "AI-powered chat backend API"
authors = [{name = "NikhilOO7", email = "your.email@example.com"}]
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.1",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy>=2.0.0",
    "psycopg2-binary>=2.9.0",
    "redis>=4.0.0",
    "openai>=1.0.0",
    "python-multipart>=0.0.6",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "alembic>=1.12.0",
    "python-dotenv>=1.0.0",
    "pydantic>=2.0.0",
    "httpx>=0.25.0"
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "mypy>=1.5.0",
    "pre-commit>=3.0.0"
]

[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
multi_line_output = 3

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"
'''
            
            pyproject_toml.write_text(pyproject_content)
            print("  ✓ Created pyproject.toml")
    
    def create_master_setup_script(self):
        """Create master setup script"""
        print("🚀 Creating master setup script...")
        
        setup_script_content = '''#!/usr/bin/env python3
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
'''
        
        setup_script = self.project_root / 'setup.py'
        setup_script.write_text(setup_script_content)
        os.chmod(setup_script, 0o755)
        print("  ✓ Created setup.py")
    
    def update_gitignore(self):
        """Update .gitignore for production"""
        print("📝 Updating .gitignore...")
        
        gitignore_content = '''# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Unit test / coverage reports
htmlcov/
.tox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
.hypothesis/
.pytest_cache/

# Environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Database
*.db
*.sqlite3

# Redis dump
dump.rdb

# Logs
logs/
*.log

# Data directories
data/postgres/*
data/redis/*
!data/postgres/.gitkeep
!data/redis/.gitkeep

# Backup
backup_before_cleanup/

# Setup files (exclude from production deployment)
setup/development/
setup/testing/
setup/scripts/
setup/documentation/
'''
        
        gitignore_path = self.project_root / '.gitignore'
        gitignore_path.write_text(gitignore_content)
        print("  ✓ Updated .gitignore")
    
    def update_readme(self):
        """Update README for production"""
        print("📚 Updating README...")
        
        readme_content = '''# Chat Backend API

A production-ready AI-powered chat backend built with FastAPI, featuring real-time chat capabilities, OpenAI integration, and comprehensive user management.

## 🚀 Quick Start

### Production Deployment
```bash
# Clone the repository
git clone https://github.com/NikhilOO7/chat-backend.git
cd chat-backend

# Setup production environment
python setup.py setup --env prod

# Start production server
python setup.py start --env prod
```

### Development Setup
```bash
# Setup development environment
python setup.py setup --env dev

# Start development server  
python setup.py start --env dev
```

## 📁 Project Structure

```
chat-backend/
├── app/                    # Application source code
│   ├── api/               # API routes and endpoints
│   ├── core/              # Core configurations
│   ├── models/            # Database models
│   ├── services/          # Business logic services
│   └── utils/             # Utility functions
├── alembic/               # Database migrations
├── tests/                 # Test suite
├── setup/                 # Development & setup tools
├── config/                # Configuration files
├── requirements.txt       # Production dependencies
├── docker-compose.yml     # Docker configuration
└── setup.py              # Master setup script
```

## 🛠️ Available Commands

```bash
# Environment setup
python setup.py setup --env dev     # Development setup
python setup.py setup --env prod    # Production setup

# Server management
python setup.py start --env dev     # Start development server
python setup.py start --env prod    # Start production server

# Testing and maintenance
python setup.py test                # Run test suite
python setup.py clean               # Clean project artifacts
```

## ⚙️ Configuration

Set the following environment variables in your `.env` file:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/chatbot_db

# Redis
REDIS_URL=redis://localhost:6379

# OpenAI
OPENAI_API_KEY=your_openai_api_key

# Security
SECRET_KEY=your_secret_key
```

## 📖 API Documentation

- **Development**: http://localhost:8000/docs
- **Production**: http://your-domain.com/docs

## 🏗️ Architecture

This backend provides:

- **RESTful API** with FastAPI
- **Real-time chat** capabilities
- **OpenAI integration** for AI responses
- **User authentication** and management
- **PostgreSQL** database with SQLAlchemy
- **Redis** for caching and sessions
- **Docker** containerization
- **Alembic** database migrations

## 🧪 Testing

```bash
# Run all tests
python setup.py test

# Run specific test files
pytest tests/unit/
pytest tests/integration/
```

## 🚀 Deployment

The application is containerized and ready for deployment on any platform supporting Docker.

### Docker Deployment
```bash
docker-compose up -d
```

### Environment Variables
Ensure all required environment variables are set in your production environment.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## 📄 License

This project is licensed under the terms specified in the LICENSE file.
'''
        
        readme_path = self.project_root / 'README.md'
        readme_path.write_text(readme_content)
        print("  ✓ Updated README.md")
    
    def print_summary(self):
        """Print cleanup summary"""
        print("\n" + "="*60)
        print("🎉 CHAT BACKEND CLEANUP COMPLETED!")
        print("="*60)
        print()
        print("📁 New Production Structure:")
        print("  ├── app/                    # Clean application code")
        print("  ├── alembic/                # Database migrations")
        print("  ├── tests/                  # Test suite")
        print("  ├── setup/                  # Development tools (organized)")
        print("  ├── config/                 # Configuration files")
        print("  ├── deployment/             # Deployment configurations")
        print("  ├── requirements.txt        # Production dependencies")
        print("  ├── docker-compose.yml      # Container configuration")
        print("  ├── pyproject.toml         # Modern Python project config")
        print("  └── setup.py               # Master setup script")
        print()
        print("🧹 Cleaned Up:")
        print("  • Moved setup scripts to setup/development/")
        print("  • Moved test files to setup/testing/")
        print("  • Moved docs to setup/documentation/")
        print("  • Cleaned data directories")
        print("  • Updated configuration files")
        print("  • Created production-ready README")
        print()
        print("🚀 Next Steps:")
        print("  1. Review the changes")
        print("  2. Test the new setup:")
        print("     python setup.py setup --env dev")
        print("     python setup.py start --env dev")
        print("  3. Commit the cleaned structure")
        print("  4. Deploy to production")
        print()
        print("💾 Backup available at: backup_before_cleanup/")
        print("="*60)
    
    def cleanup(self):
        """Main cleanup process"""
        print("🚀 Starting Chat Backend cleanup...")
        print(f"📂 Project root: {self.project_root}")
        
        try:
            # Step 1: Create backup
            self.create_backup()
            
            # Step 2: Create new structure
            self.create_new_structure()
            
            # Step 3: Move setup files
            self.move_setup_files()
            
            # Step 4: Clean data directories  
            self.clean_data_directories()
            
            # Step 5: Remove outdated files
            self.remove_project_structure_md()
            
            # Step 6: Create production configs
            self.create_production_configs()
            
            # Step 7: Create master setup script
            self.create_master_setup_script()
            
            # Step 8: Update .gitignore
            self.update_gitignore()
            
            # Step 9: Update README
            self.update_readme()
            
            # Step 10: Print summary
            self.print_summary()
            
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            print(f"💾 Your original files are safe in: {self.backup_dir}")
            sys.exit(1)

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up Chat Backend project")
    parser.add_argument("--project-root", default=".", help="Project root directory")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    
    args = parser.parse_args()
    
    cleanup = ChatBackendCleanup(args.project_root)
    
    if args.dry_run:
        print("🔍 DRY RUN - No changes will be made")
        print("\nFiles that would be moved:")
        print("\nTo setup/development/:")
        for file in cleanup.setup_files:
            if not file.startswith('test_'):
                print(f"  - {file}")
        
        print("\nTo setup/testing/:")
        for file in cleanup.setup_files:
            if file.startswith('test_'):
                print(f"  - {file}")
        
        print("\nDirectories to reorganize:")
        for dir_name in cleanup.setup_dirs:
            print(f"  - {dir_name}/")
        
        print("\nFiles to be created:")
        print("  - setup.py (master setup script)")
        print("  - pyproject.toml")
        print("  - alembic.ini")
        print("  - .env.example")
        print("  - Updated .gitignore")
        print("  - Updated README.md")
        
    else:
        cleanup.cleanup()

if __name__ == "__main__":
    main()
