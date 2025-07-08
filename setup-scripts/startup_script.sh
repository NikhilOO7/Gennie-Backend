#!/bin/bash

# AI Chatbot Backend - Enhanced Startup Script with Better Debugging
# This script includes better error handling and server startup diagnostics

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}=================================${NC}"
}

# Check if .env file exists
check_env_file() {
    if [ ! -f .env ]; then
        print_error ".env file not found!"
        echo "Creating .env file from your provided configuration..."
        
        cat > .env << EOF
# Database Configuration
DATABASE_URL=postgresql://chatbot_user:chatbot_password@localhost:5432/chatbot_db
POSTGRES_USER=chatbot_user
POSTGRES_PASSWORD=chatbot_password
POSTGRES_DB=chatbot_db

# Redis Configuration
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379

# OpenAI Configuration (update with your actual key)
OPENAI_API_KEY=${OPENAI_API_KEY:-sk-your-openai-key-here}
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7
OPENAI_MAX_TOKENS=1000
EMBEDDINGS_MODEL=text-embedding-ada-002

# Security Configuration
SECRET_KEY=${SECRET_KEY:-your-super-secret-key-change-this-in-production-minimum-32-characters}
ALGORITHM=HS256
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:8080,http://127.0.0.1:3000,*

# Application Configuration
ENVIRONMENT=development
DEBUG=True
EOF
        print_status ".env file created successfully!"
    else
        print_status ".env file found!"
    fi
}

# Check dependencies
check_dependencies() {
    print_header "CHECKING DEPENDENCIES"
    
    # Check Python
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version)
        print_status "Python found: $PYTHON_VERSION"
    else
        print_error "Python 3 is required but not installed!"
        exit 1
    fi
    
    # Check Docker
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version)
        print_status "Docker found: $DOCKER_VERSION"
    else
        print_error "Docker is required but not installed!"
        exit 1
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version)
        print_status "Docker Compose found: $COMPOSE_VERSION"
    else
        print_error "Docker Compose is required but not installed!"
        exit 1
    fi
}

# Setup virtual environment
setup_venv() {
    print_header "SETTING UP VIRTUAL ENVIRONMENT"
    
    if [ ! -d "venv" ]; then
        print_status "Creating virtual environment..."
        python3 -m venv venv
    fi
    
    print_status "Activating virtual environment..."
    source venv/bin/activate
    
    print_status "Upgrading pip..."
    pip install --upgrade pip
    
    print_status "Installing Python dependencies..."
    pip install -r requirements.txt
    
    print_status "Virtual environment setup complete!"
}

# Start Docker services
start_docker_services() {
    print_header "STARTING DOCKER SERVICES"
    
    print_status "Stopping any existing services..."
    docker-compose down || true
    
    print_status "Starting PostgreSQL and Redis..."
    docker-compose up -d postgres redis
    
    print_status "Waiting for services to be ready..."
    sleep 15
    
    # Check if services are healthy
    print_status "Checking service health..."
    
    # Check PostgreSQL with more attempts
    max_attempts=60
    attempt=1
    while [ $attempt -le $max_attempts ]; do
        if docker-compose exec -T postgres pg_isready -U chatbot_user -d chatbot_db &> /dev/null; then
            print_status "PostgreSQL is ready!"
            break
        fi
        print_warning "Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done
    
    if [ $attempt -gt $max_attempts ]; then
        print_error "PostgreSQL failed to start!"
        print_error "Checking PostgreSQL logs..."
        docker-compose logs postgres
        exit 1
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping &> /dev/null; then
        print_status "Redis is ready!"
    else
        print_error "Redis failed to start!"
        print_error "Checking Redis logs..."
        docker-compose logs redis
        exit 1
    fi
}

# Test database connection manually
test_database() {
    print_header "TESTING DATABASE CONNECTION"
    
    print_status "Testing database connection..."
    source venv/bin/activate
    
    # Create a simple test script
    cat > test_db_connection.py << 'EOF'
import sys
import os
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

# Add current directory to path
sys.path.insert(0, os.getcwd())

async def test_connection():
    try:
        from app.config import settings
        print(f"✅ Settings loaded successfully")
        print(f"   Database URL: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'hidden'}")
        
        # Test basic connection
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Database connection successful!")
            print(f"   PostgreSQL version: {version.split()[1]}")
        
        # Test Redis
        from app.database import get_redis
        redis_client = await get_redis()
        await redis_client.ping()
        print(f"✅ Redis connection successful!")
        
        # Test table creation
        from app.database import create_tables
        success = await create_tables()
        if success:
            print(f"✅ Database tables created/verified!")
        else:
            print(f"❌ Failed to create database tables!")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_connection())
    sys.exit(0 if result else 1)
EOF
    
    if python test_db_connection.py; then
        print_status "Database tests passed!"
        rm test_db_connection.py
        return 0
    else
        print_error "Database tests failed!"
        rm test_db_connection.py
        return 1
    fi
}

# Enhanced server startup with better diagnostics
start_server() {
    print_header "STARTING FASTAPI SERVER"
    
    source venv/bin/activate
    
    # Kill any existing Python processes on port 8000
    print_status "Checking for existing processes on port 8000..."
    if lsof -ti:8000 &> /dev/null; then
        print_warning "Port 8000 is in use. Killing existing processes..."
        kill -9 $(lsof -ti:8000) 2>/dev/null || true
        sleep 2
    fi
    
    # Test import before starting server
    print_status "Testing app imports..."
    python -c "
import sys
import os
sys.path.insert(0, os.getcwd())
try:
    from app.main import app
    print('✅ App imports successful!')
except Exception as e:
    print(f'❌ App import failed: {e}')
    sys.exit(1)
" || {
        print_error "App import failed! Cannot start server."
        return 1
    }
    
    # Start server with more verbose logging
    print_status "Starting FastAPI server with detailed logging..."
    
    # Create a startup log file
    nohup uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --reload \
        --log-level info \
        --access-log \
        > server_startup.log 2>&1 &
    
    SERVER_PID=$!
    echo $SERVER_PID > server.pid
    
    print_status "Server started with PID: $SERVER_PID"
    print_status "Waiting for server to initialize..."
    
    # Wait longer and check more thoroughly
    for i in {1..30}; do
        sleep 2
        
        # Check if process is still running
        if ! kill -0 $SERVER_PID 2>/dev/null; then
            print_error "Server process died! Check logs:"
            cat server_startup.log
            return 1
        fi
        
        # Check if server is responding
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            print_status "Server is responding! (attempt $i)"
            return 0
        fi
        
        if [ $i -eq 10 ] || [ $i -eq 20 ]; then
            print_warning "Server not ready yet... (attempt $i/30)"
            print_warning "Recent logs:"
            tail -10 server_startup.log
        fi
    done
    
    print_error "Server failed to start properly!"
    print_error "Full startup log:"
    cat server_startup.log
    return 1
}

# Enhanced API testing
test_endpoints() {
    print_header "TESTING API ENDPOINTS"
    
    # Test health endpoint with detailed output
    print_status "Testing health endpoint..."
    HEALTH_RESPONSE=$(curl -s -w "HTTP_CODE:%{http_code}" http://localhost:8000/health)
    HTTP_CODE=$(echo "$HEALTH_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    RESPONSE_BODY=$(echo "$HEALTH_RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_status "✅ Health endpoint working!"
        echo "   Response: $RESPONSE_BODY"
    else
        print_error "❌ Health endpoint failed! HTTP Code: $HTTP_CODE"
        echo "   Response: $RESPONSE_BODY"
        return 1
    fi
    
    # Test root endpoint
    print_status "Testing root endpoint..."
    ROOT_RESPONSE=$(curl -s -w "HTTP_CODE:%{http_code}" http://localhost:8000/)
    HTTP_CODE=$(echo "$ROOT_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    
    if [ "$HTTP_CODE" = "200" ]; then
        print_status "✅ Root endpoint working!"
    else
        print_error "❌ Root endpoint failed! HTTP Code: $HTTP_CODE"
        return 1
    fi
    
    # Test user registration
    print_status "Testing user registration..."
    REGISTER_RESPONSE=$(curl -s -w "HTTP_CODE:%{http_code}" -X POST "http://localhost:8000/api/auth/register" \
        -H "Content-Type: application/json" \
        -d '{
            "email": "demo@example.com",
            "username": "demouser",
            "password": "demopassword123",
            "first_name": "Demo",
            "last_name": "User"
        }')
    
    HTTP_CODE=$(echo "$REGISTER_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
    RESPONSE_BODY=$(echo "$REGISTER_RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')
    
    if [ "$HTTP_CODE" = "201" ]; then
        print_status "✅ User registration working!"
        
        # Test login
        print_status "Testing user login..."
        LOGIN_RESPONSE=$(curl -s -w "HTTP_CODE:%{http_code}" -X POST "http://localhost:8000/api/auth/login" \
            -H "Content-Type: application/json" \
            -d '{
                "email": "demo@example.com",
                "password": "demopassword123"
            }')
        
        LOGIN_HTTP_CODE=$(echo "$LOGIN_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
        LOGIN_BODY=$(echo "$LOGIN_RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')
        
        if [ "$LOGIN_HTTP_CODE" = "200" ]; then
            print_status "✅ User login working!"
            
            # Extract token for further tests
            TOKEN=$(echo "$LOGIN_BODY" | python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")
            
            if [ -n "$TOKEN" ]; then
                # Test creating a chat
                print_status "Testing chat creation..."
                CHAT_RESPONSE=$(curl -s -w "HTTP_CODE:%{http_code}" -X POST "http://localhost:8000/api/chats/" \
                    -H "Content-Type: application/json" \
                    -H "Authorization: Bearer $TOKEN" \
                    -d '{"title": "Demo Chat", "description": "This is a demo chat"}')
                
                CHAT_HTTP_CODE=$(echo "$CHAT_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
                
                if [ "$CHAT_HTTP_CODE" = "201" ]; then
                    print_status "✅ Chat creation working!"
                else
                    print_warning "⚠️  Chat creation failed. HTTP Code: $CHAT_HTTP_CODE"
                    echo "   Response: $(echo "$CHAT_RESPONSE" | sed 's/HTTP_CODE:[0-9]*$//')"
                fi
            fi
        else
            print_error "❌ User login failed! HTTP Code: $LOGIN_HTTP_CODE"
            echo "   Response: $LOGIN_BODY"
        fi
    else
        if [ "$HTTP_CODE" = "400" ] && echo "$RESPONSE_BODY" | grep -q "already registered\|already taken"; then
            print_warning "⚠️  User already exists, trying login instead..."
            
            # Try login with existing user
            LOGIN_RESPONSE=$(curl -s -w "HTTP_CODE:%{http_code}" -X POST "http://localhost:8000/api/auth/login" \
                -H "Content-Type: application/json" \
                -d '{
                    "email": "demo@example.com",
                    "password": "demopassword123"
                }')
            
            LOGIN_HTTP_CODE=$(echo "$LOGIN_RESPONSE" | grep -o "HTTP_CODE:[0-9]*" | cut -d: -f2)
            
            if [ "$LOGIN_HTTP_CODE" = "200" ]; then
                print_status "✅ Login with existing user successful!"
            else
                print_error "❌ Login with existing user failed! HTTP Code: $LOGIN_HTTP_CODE"
            fi
        else
            print_error "❌ User registration failed! HTTP Code: $HTTP_CODE"
            echo "   Response: $RESPONSE_BODY"
        fi
    fi
    
    return 0
}

# Cleanup function
cleanup() {
    print_status "Cleaning up..."
    if [ -f server.pid ]; then
        SERVER_PID=$(cat server.pid)
        if kill -0 $SERVER_PID 2>/dev/null; then
            print_status "Stopping server (PID: $SERVER_PID)..."
            kill $SERVER_PID
        fi
        rm server.pid
    fi
}

# Trap cleanup on script exit
trap cleanup EXIT

# Main demo setup function
main() {
    print_header "AI CHATBOT BACKEND - ENHANCED DEMO SETUP"
    print_status "Starting complete setup with enhanced diagnostics..."
    
    # Check if we're in the right directory
    if [ ! -f "requirements.txt" ]; then
        print_error "Please run this script from the project root directory!"
        exit 1
    fi
    
    check_env_file
    check_dependencies
    setup_venv
    start_docker_services
    
    if ! test_database; then
        print_error "Database tests failed! Cannot continue."
        exit 1
    fi
    
    if ! start_server; then
        print_error "Server failed to start! Cannot continue."
        exit 1
    fi
    
    if ! test_endpoints; then
        print_warning "Some endpoint tests failed, but server is running."
    fi
    
    print_header "DEMO SETUP COMPLETE!"
    print_status "🎉 Your AI Chatbot Backend is ready!"
    echo ""
    print_status "Server Information:"
    echo "  • API URL: http://localhost:8000"
    echo "  • API Docs: http://localhost:8000/docs"
    echo "  • Health Check: http://localhost:8000/health"
    echo "  • Server PID: $(cat server.pid 2>/dev/null || echo 'Not found')"
    echo ""
    print_status "Useful Commands:"
    echo "  • View live logs: tail -f server_startup.log"
    echo "  • Stop server: kill \$(cat server.pid)"
    echo "  • Stop services: docker-compose down"
    echo ""
    print_status "Demo User Credentials:"
    echo "  • Email: demo@example.com"
    echo "  • Password: demopassword123"
    echo ""
    print_status "🚀 Ready for your demo! The server will keep running in the background."
}

# Handle script interruption
trap 'print_error "Setup interrupted!"; cleanup; exit 1' INT

# Run main function
main "$@"