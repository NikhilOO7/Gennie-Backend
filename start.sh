#!/bin/bash
# Quick start script for AI Chatbot Backend

echo "🚀 Starting AI Chatbot Backend..."

# Check if setup has been run
if [[ ! -d "venv" ]] || [[ ! -d "alembic" ]]; then
    echo "⚠️  Setup not completed. Running setup first..."
    ./setup.sh
fi

# Activate virtual environment
source venv/bin/activate

# Start Docker services if not running
if ! docker-compose ps | grep -q "Up"; then
    echo "🐳 Starting Docker services..."
    docker-compose up -d postgres redis
    echo "⏳ Waiting for services to be ready..."
    sleep 10
fi

# Start the application
echo "🎯 Starting FastAPI application..."
echo "📖 API Docs: http://localhost:8000/docs"
echo "🏥 Health Check: http://localhost:8000/health"
echo "🛑 Press Ctrl+C to stop"
echo ""

uvicorn app.main:app --reload --host 0.0.0.0 --port 8000