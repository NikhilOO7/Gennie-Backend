#!/bin/bash

echo "🔧 AI Chatbot Backend - Project Restructuring Guide"
echo "=================================================="

# This script will help you restructure your project step by step

echo "Step 1: Create backup and clean unnecessary files"
echo "📝 Run these commands:"
echo ""

cat << 'EOF'
# Create timestamped backup
cp -r . "../backup_$(date +%Y%m%d_%H%M%S)"

# Remove Python cache files
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

# Remove testing artifacts
rm -rf .pytest_cache .coverage htmlcov .mypy_cache 2>/dev/null || true

# Remove logs and temp files
find . -name "*.log" -delete 2>/dev/null || true
find . -name "*.tmp" -delete 2>/dev/null || true
find . -name "*.temp" -delete 2>/dev/null || true

# Remove OS files
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "Thumbs.db" -delete 2>/dev/null || true

echo "✅ Cleanup completed"
EOF

echo ""
echo "Step 2: Create new directory structure"
echo "📝 Run these commands:"
echo ""

cat << 'EOF'
# Create new API structure
mkdir -p app/api/v1/endpoints
mkdir -p app/core
mkdir -p app/models
mkdir -p app/services
mkdir -p app/utils
mkdir -p tests/{unit,integration}
mkdir -p scripts
mkdir -p docs

# Create __init__.py files
touch app/__init__.py
touch app/api/__init__.py
touch app/api/v1/__init__.py
touch app/api/v1/endpoints/__init__.py
touch app/{core,models,services,utils}/__init__.py
touch tests/__init__.py
touch tests/{unit,integration}/__init__.py

echo "✅ Directory structure created"
EOF

echo ""
echo "Step 3: Move existing files to new structure"
echo "📝 If you have existing files, move them:"
echo ""

cat << 'EOF'
# Move routers to new API endpoints
if [ -d "app/routers" ]; then
    mv app/routers/* app/api/v1/endpoints/ 2>/dev/null || true
    rmdir app/routers 2>/dev/null || true
    echo "✅ Moved routers to API endpoints"
fi

# Ensure core files are in place
if [ -f "app/config.py" ]; then
    mv app/config.py app/core/
    echo "✅ Moved config.py to core/"
fi

if [ -f "app/database.py" ]; then
    mv app/database.py app/core/
    echo "✅ Moved database.py to core/"
fi

# Services should already be in app/services/
# Models should already be in app/models/
# schemas.py should stay in app/
EOF

echo ""
echo "Step 4: Create essential configuration files"
echo "📝 Create these files:"
echo ""

echo "Creating .gitignore..."
cat > .gitignore << 'GITIGNORE_EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
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

# Virtual Environment
venv/
ENV/
env/
.venv/

# IDE
.vscode/settings.json
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
Thumbs.db

# Logs
*.log
logs/

# Database
*.db
*.sqlite3

# Environment
.env
.env.local

# Testing
.pytest_cache/
.coverage
htmlcov/
.mypy_cache/

# Temporary
*.tmp
*.temp
*.bak
GITIGNORE_EOF

echo "✅ .gitignore created"

echo ""
echo "Creating app/api/v1/api.py..."
cat > app/api/v1/api.py << 'API_EOF'
from fastapi import APIRouter
from app.api.v1.endpoints import health, chat, ai

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(
    health.router,
    prefix="/health",
    tags=["Health Check"]
)

api_router.include_router(
    chat.router,
    prefix="/chat",
    tags=["Chat Management"]
)

api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI Conversation"]
)
API_EOF

echo "✅ API aggregation file created"

echo ""
echo "Step 5: Update main.py"
echo "📝 Update your app/main.py file:"
echo ""

cat << 'MAIN_EOF'
# Updated app/main.py structure
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info(f"Starting {settings.project_name} v{settings.project_version}")
    logger.info(f"Environment: {settings.environment}")
    
    # Test database connection
    from app.core.database import test_database_connection, test_redis_connection
    
    if test_database_connection():
        logger.info("Database connection successful")
    else:
        logger.error("Database connection failed")
        
    if await test_redis_connection():
        logger.info("Redis connection successful")
    else:
        logger.error("Redis connection failed")
    
    yield
    
    # Shutdown
    logger.info(f"Shutting down {settings.project_name}")
    from app.core.database import redis_client
    await redis_client.close()

# Create FastAPI application
app = FastAPI(
    title=settings.project_name,
    description="Backend API for AI-powered conversational chatbot",
    version=settings.project_version,
    debug=settings.debug,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": f"Welcome to {settings.project_name}",
        "version": settings.project_version,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
        "docs_url": "/docs" if settings.debug else "Documentation disabled",
        "status": "running"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )
MAIN_EOF

echo "✅ main.py structure example created"

echo ""
echo "Step 6: Update import statements"
echo "📝 Update imports in your endpoint files:"
echo ""

cat << 'IMPORT_EOF'
# In your endpoint files (app/api/v1/endpoints/*.py), update imports:

# OLD imports:
# from app.routers import health, auth, chat, ai
# from app.core.config import settings
# from app.core.database import get_db

# NEW imports (these should work with new structure):
from app.core.config import settings
from app.core.database import get_db, get_redis
from app.models.chat import Chat, Message
from app.models.user import User
from app.services.openai_service import openai_service
from app.services.prompt_service import prompt_service
from app.schemas import ConversationRequest, ConversationResponse
IMPORT_EOF

echo "✅ Import examples provided"

echo ""
echo "Step 7: Test the restructured application"
echo "📝 Run these commands to test:"
echo ""

cat << 'TEST_EOF'
# Activate virtual environment
source venv/bin/activate

# Test imports
python -c "from app.main import app; print('✅ App imports successfully')"
python -c "from app.core.config import settings; print('✅ Config imports successfully')"
python -c "from app.core.database import get_db; print('✅ Database imports successfully')"

# Fix database permissions (if needed)
./fix_db_permissions.sh

# Start the application
uvicorn app.main:app --reload

# Test endpoints
curl http://localhost:8000/
curl http://localhost:8000/api/v1/health
TEST_EOF

echo ""
echo "🎉 Project restructuring guide completed!"
echo ""
echo "📋 Next steps:"
echo "1. Follow the steps above in order"
echo "2. Update any remaining import statements"
echo "3. Test the application thoroughly"
echo "4. Update documentation"
echo "5. Commit the cleaned structure to git"
echo ""
echo "💡 Benefits of this structure:"
echo "- Easier debugging and maintenance"
echo "- Better separation of concerns"
echo "- Scalable for future features"
echo "- Industry standard FastAPI structure"