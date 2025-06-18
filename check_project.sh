#!/bin/bash
# Check project structure and requirements

echo "🔍 Checking AI Chatbot Backend Project Structure..."
echo "=================================================="

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

check_file() {
    if [[ -f "$1" ]]; then
        echo -e "${GREEN}✅ $1${NC}"
        return 0
    else
        echo -e "${RED}❌ $1 (missing)${NC}"
        return 1
    fi
}

check_dir() {
    if [[ -d "$1" ]]; then
        echo -e "${GREEN}✅ $1/${NC}"
        return 0
    else
        echo -e "${RED}❌ $1/ (missing)${NC}"
        return 1
    fi
}

echo "📁 Required Files:"
check_file "requirements.txt"
check_file "docker-compose.yml"
check_file ".env"
check_file "setup.sh"

echo ""
echo "📂 Required Directories:"
check_dir "app"
check_dir "app/core"
check_dir "app/models"
check_dir "app/routers"
check_dir "app/services"

echo ""
echo "🐍 Core Python Files:"
check_file "app/__init__.py"
check_file "app/main.py"
check_file "app/schemas.py"
check_file "app/core/config.py"
check_file "app/core/database.py"

echo ""
echo "📊 Model Files:"
check_file "app/models/user.py"
check_file "app/models/chat.py"
check_file "app/models/user_preference.py"

echo ""
echo "🛣️  Router Files:"
check_file "app/routers/__init__.py"
check_file "app/routers/health.py"
check_file "app/routers/auth.py"
check_file "app/routers/chat.py"
check_file "app/routers/ai.py"

echo ""
echo "⚙️  Service Files:"
check_file "app/services/__init__.py"
check_file "app/services/openai_service.py"
check_file "app/services/prompt_service.py"

echo ""
echo "🔧 Environment Check:"
if [[ -f ".env" ]]; then
    if grep -q "your_openai_api_key_here" .env; then
        echo -e "${YELLOW}⚠️  OpenAI API key needs to be set in .env${NC}"
    else
        echo -e "${GREEN}✅ OpenAI API key is configured${NC}"
    fi
else
    echo -e "${RED}❌ .env file missing${NC}"
fi

echo ""
echo "🐳 Docker Check:"
if command -v docker &> /dev/null; then
    if docker info &> /dev/null; then
        echo -e "${GREEN}✅ Docker is running${NC}"
    else
        echo -e "${YELLOW}⚠️  Docker is installed but not running${NC}"
    fi
else
    echo -e "${RED}❌ Docker is not installed${NC}"
fi

echo ""
echo "🐍 Python Environment:"
if [[ -d "venv" ]]; then
    echo -e "${GREEN}✅ Virtual environment exists${NC}"
else
    echo -e "${YELLOW}⚠️  Virtual environment not created${NC}"
fi

echo ""
echo "📋 Next Steps:"
echo "1. Run: chmod +x setup.sh"
echo "2. Run: ./setup.sh"
echo "3. Add your OpenAI API key to .env file"
echo "4. Run: ./start.sh"