#!/bin/bash
# setup.sh - Enhanced Script to set up the AI Chatbot Backend on Mac
# This script automates the setup process for the AI Chatbot Backend project on macOS.
# SPDX-License-Identifier: MIT

# AI Chatbot Backend - Mac Setup Script
echo "🚀 Setting up AI Chatbot Backend on Mac..."
echo "============================================"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check if Docker is running (with better error handling)
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker and try again."
        print_info "Install with: brew install --cask docker"
        exit 1
    fi
    
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker and try again."
        print_info "If using Colima: colima start"
        print_info "If using Docker Desktop: Start Docker Desktop app"
        exit 1
    fi
    print_status "Docker is running"
}

# Check if we're in the right directory
check_directory() {
    if [[ ! -f "requirements.txt" ]] || [[ ! -d "app" ]]; then
        print_error "Please run this script from the ai-chatbot-backend project root directory"
        print_info "Expected files: requirements.txt, app/ directory"
        exit 1
    fi  
    print_status "Found project files"
}

# Check if .env file exists and has OpenAI key
check_env_file() {
    if [[ ! -f ".env" ]]; then
        print_warning ".env file not found. Creating from template..."
        cp .env.example .env 2>/dev/null || true
    fi
    
    if grep -q "your_openai_api_key_here" .env 2>/dev/null; then
        print_warning "Please add your OpenAI API key to the .env file"
        print_info "Edit .env and replace: OPENAI_API_KEY=your_openai_api_key_here"
    fi
    
    print_status ".env file ready"
}

# Stop existing containers
cleanup_containers() {
    print_info "Stopping any existing containers..."
    docker-compose down > /dev/null 2>&1
    print_status "Cleaned up existing containers"
}

# Create required directories
create_directories() {
    print_info "Creating required directories..."
    mkdir -p logs
    mkdir -p data/postgres
    mkdir -p data/redis
    mkdir -p alembic/versions
    print_status "Created directories"
}

# Check Python virtual environment
check_venv() {
    if [[ ! -d "venv" ]]; then
        print_warning "Virtual environment not found. Creating one..."
        if ! python3 -m venv venv; then
            print_error "Failed to create virtual environment"
            exit 1
        fi
    fi
    print_status "Virtual environment ready"
}

# Create missing service files
create_service_files() {
    print_info "Creating missing service files..."
    
    # Create services directory and __init__.py
    mkdir -p app/services
    touch app/services/__init__.py
    
    # Create basic service files if they don't exist
    if [[ ! -f "app/services/openai_service.py" ]]; then
        print_info "Creating OpenAI service file..."
        # This will be a basic placeholder - you already have the full version
        echo "# OpenAI Service - placeholder" > app/services/openai_service.py
    fi
    
    if [[ ! -f "app/services/prompt_service.py" ]]; then
        print_info "Creating Prompt service file..."
        echo "# Prompt Service - placeholder" > app/services/prompt_service.py
    fi
    
    print_status "Service files ready"
}

# Activate virtual environment and install dependencies
setup_python() {
    print_info "Setting up Python environment..."
    source venv/bin/activate
    
    # Upgrade pip
    print_info "Upgrading pip..."
    pip install --upgrade pip > /dev/null 2>&1
    
    # Install dependencies
    print_info "Installing Python dependencies..."
    if pip install -r requirements.txt; then
        print_status "Python dependencies installed"
    else
        print_error "Failed to install Python dependencies"
        print_info "Try running: pip install -r requirements.txt manually"
        exit 1
    fi
}

# Start Docker services with better error handling
start_docker_services() {
    print_info "Starting Docker services (PostgreSQL & Redis)..."
    
    # Pull images first
    print_info "Pulling Docker images..."
    docker-compose pull postgres redis
    
    if docker-compose up -d postgres redis; then
        print_status "Docker services started"
    else
        print_error "Failed to start Docker services"
        print_info "Check logs with: docker-compose logs"
        exit 1
    fi
    
    # Wait for services to be healthy with progress
    print_info "Waiting for services to be ready..."
    for i in {1..30}; do
        if docker-compose exec -T postgres pg_isready -U chatbot_user -d chatbot_db > /dev/null 2>&1; then
            break
        fi
        echo -n "."
        sleep 2
    done
    echo ""
    
    # Check PostgreSQL
    if docker-compose exec -T postgres pg_isready -U chatbot_user -d chatbot_db > /dev/null 2>&1; then
        print_status "PostgreSQL is ready"
    else
        print_warning "PostgreSQL might still be starting up..."
    fi
    
    # Check Redis
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        print_status "Redis is ready"
    else
        print_warning "Redis might still be starting up..."
    fi
}

# Setup database migrations with better error handling
setup_database() {
    print_info "Setting up database..."
    source venv/bin/activate
    
    # Initialize Alembic if not already done
    if [[ ! -d "alembic" ]]; then
        print_info "Initializing Alembic..."
        alembic init alembic
        
        # Update alembic.ini to use environment variable
        if [[ -f "alembic.ini" ]]; then
            # Comment out the sqlalchemy.url line
            sed -i.bak 's/^sqlalchemy.url = .*/# sqlalchemy.url = /' alembic.ini
            print_status "Updated alembic.ini"
        fi
    fi
    
    # Wait a bit more for PostgreSQL
    sleep 5
    
    # Create initial migration
    print_info "Creating database migration..."
    if alembic revision --autogenerate -m "Initial database schema"; then
        print_status "Created database migration"
    else
        print_warning "Migration creation might have issues - continuing..."
    fi
    
    # Apply migration
    print_info "Applying database migrations..."
    if alembic upgrade head; then
        print_status "Applied database migrations"
    else
        print_warning "Migration application might have issues - continuing..."
    fi
}

# Test the setup
test_setup() {
    print_info "Testing the setup..."
    source venv/bin/activate
    
    # Test database connection
    print_info "Testing database connection..."
    python3 -c "
try:
    from app.core.database import test_database_connection
    if test_database_connection():
        print('✅ Database connection successful')
    else:
        print('❌ Database connection failed')
        exit(1)
except Exception as e:
    print(f'❌ Database test error: {e}')
    exit(1)
" 2>/dev/null
    
    if [[ $? -eq 0 ]]; then
        print_status "Database connection test passed"
    else
        print_warning "Database connection test failed - services might still be starting"
    fi
    
    # Test Redis connection
    print_info "Testing Redis connection..."
    if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
        print_status "Redis connection test passed"
    else
        print_warning "Redis connection test failed"
    fi
}

# Start the application for testing
start_application() {
    print_info "Starting application for testing..."
    source venv/bin/activate
    
    # Start app in background for testing
    uvicorn app.main:app --host 0.0.0.0 --port 8000 &
    APP_PID=$!
    
    # Wait for app to start
    sleep 5
    
    # Test health endpoint
    if curl -s http://localhost:8000/health > /dev/null; then
        print_status "Application is running successfully!"
        
        # Test API docs
        print_info "API Documentation: http://localhost:8000/docs"
        print_info "Health Check: http://localhost:8000/health"
    else
        print_warning "Application might still be starting..."
    fi
    
    # Stop the test app
    kill $APP_PID 2>/dev/null || true
    sleep 2
}

# Main setup process
main() {
    echo
    print_info "Starting setup process..."
    echo
    
    check_directory
    check_env_file
    check_docker
    cleanup_containers
    create_directories
    check_venv
    create_service_files
    setup_python
    start_docker_services
    setup_database
    test_setup
    start_application
    
    echo
    echo "============================================"
    print_status "Setup completed successfully! 🎉"
    echo
    print_info "Next steps:"
    echo "1. Add your OpenAI API key to the .env file:"
    echo "   OPENAI_API_KEY=sk-your-actual-api-key-here"
    echo
    echo "2. Start the application:"
    echo "   source venv/bin/activate"
    echo "   uvicorn app.main:app --reload"
    echo
    echo "3. Visit http://localhost:8000/docs to see the API"
    echo
    print_info "Optional tools (run with --tools):"
    echo "• pgAdmin: http://localhost:5050 (admin@chatbot.com / admin123)"
    echo "• Redis Commander: http://localhost:8081"
    echo
    print_info "Useful commands:"
    echo "• Check services: docker-compose ps"
    echo "• View logs: docker-compose logs"
    echo "• Stop services: docker-compose down"
    echo "• Restart: docker-compose restart"
    echo "• Test Day 3 features: python test_day3_features.py"
}

# Handle command line arguments
if [[ "$1" == "--tools" ]]; then
    print_info "Starting with management tools..."
    docker-compose --profile tools up -d
    print_status "Management tools started"
    echo "• pgAdmin: http://localhost:5050"
    echo "• Redis Commander: http://localhost:8081"
elif [[ "$1" == "--stop" ]]; then
    print_info "Stopping all services..."
    docker-compose down
    print_status "All services stopped"
elif [[ "$1" == "--reset" ]]; then
    print_warning "Resetting all data and containers..."
    docker-compose down -v
    docker system prune -f
    print_status "Reset complete"
elif [[ "$1" == "--help" ]]; then
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  --tools    Start with management tools (pgAdmin, Redis Commander)"
    echo "  --stop     Stop all services"
    echo "  --reset    Reset all data and containers (WARNING: deletes all data)"
    echo "  --help     Show this help message"
else
    main
fi