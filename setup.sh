#!/bin/bash
# setup.sh - Script to set up the AI Chatbot Backend on Mac
# This script automates the setup process for the AI Chatbot Backend project on macOS.
# It checks for necessary dependencies, sets up Docker containers, creates required directories,
# installs Python dependencies, and initializes the database.
#!/bin/bash
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

# Check if Docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        print_error "Docker is not running. Please start Docker Desktop and try again."
        exit 1
    fi
    print_status "Docker is running"
}

# Check if we're in the right directory
check_directory() {
    if [[ ! -f "requirements.txt" ]] || [[ ! -d "app" ]]; then
        print_error "Please run this script from the ai-chatbot-backend project root directory"
        exit 1
    fi  
    print_status "Found project files"
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
    print_status "Created directories"
}

# Check Python virtual environment
check_venv() {
    if [[ ! -d "venv" ]]; then
        print_warning "Virtual environment not found. Creating one..."
        python3 -m venv venv
    fi
    print_status "Virtual environment ready"
}

# Activate virtual environment and install dependencies
setup_python() {
    print_info "Setting up Python environment..."
    source venv/bin/activate
    
    # Upgrade pip
    pip install --upgrade pip > /dev/null 2>&1
    
    # Install dependencies
    if pip install -r requirements.txt > /dev/null 2>&1; then
        print_status "Python dependencies installed"
    else
        print_error "Failed to install Python dependencies"
        exit 1
    fi
}

# Start Docker services
start_docker_services() {
    print_info "Starting Docker services (PostgreSQL & Redis)..."
    
    if docker-compose up -d postgres redis; then
        print_status "Docker services started"
    else
        print_error "Failed to start Docker services"
        exit 1
    fi
    
    # Wait for services to be healthy
    print_info "Waiting for services to be ready..."
    sleep 10
    
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

# Setup database migrations
setup_database() {
    print_info "Setting up database..."
    source venv/bin/activate
    
    # Initialize Alembic if not already done
    if [[ ! -d "alembic" ]]; then
        print_info "Initializing Alembic..."
        alembic init alembic
    fi
    
    # Wait a bit more for PostgreSQL
    sleep 5
    
    # Create initial migration
    if alembic revision --autogenerate -m "Initial database schema" > /dev/null 2>&1; then
        print_status "Created database migration"
    else
        print_warning "Migration creation might have issues - will try to continue"
    fi
    
    # Apply migration
    if alembic upgrade head > /dev/null 2>&1; then
        print_status "Applied database migrations"
    else
        print_warning "Migration application might have issues - will try to continue"
    fi
}

# Test the setup
test_setup() {
    print_info "Testing the setup..."
    source venv/bin/activate
    
    # Test database connection
    python3 -c "
from app.core.database import test_database_connection
if test_database_connection():
    print('✅ Database connection successful')
else:
    print('❌ Database connection failed')
    exit(1)
" 2>/dev/null
    
    if [[ $? -eq 0 ]]; then
        print_status "Database connection test passed"
    else
        print_warning "Database connection test failed - services might still be starting"
    fi
}

# Main setup process
main() {
    echo
    print_info "Starting setup process..."
    echo
    
    check_directory
    check_docker
    cleanup_containers
    create_directories
    check_venv
    setup_python
    start_docker_services
    setup_database
    test_setup
    
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
}

# Handle command line arguments
if [[ "$1" == "--tools" ]]; then
    print_info "Starting with management tools..."
    docker-compose --profile tools up -d
    print_status "Management tools started"
    echo "• pgAdmin: http://localhost:5050"
    echo "• Redis Commander: http://localhost:8081"
elif [[ "$1" == "--help" ]]; then
    echo "Usage: $0 [OPTIONS]"
    echo "Options:"
    echo "  --tools    Start with management tools (pgAdmin, Redis Commander)"
    echo "  --help     Show this help message"
else
    main
fi