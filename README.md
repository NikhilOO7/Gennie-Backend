# 🤖 AI Chatbot Backend

> A production-ready, feature-rich AI-powered conversational backend built with FastAPI, featuring real-time chat capabilities, OpenAI integration, emotion detection, and comprehensive user management.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00a000?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?style=flat&logo=postgresql)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7.0+-dc382d?style=flat&logo=redis)](https://redis.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-API-412991?style=flat&logo=openai)](https://openai.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker)](https://docker.com)

## ✨ Features

### 🚀 Core Functionality
- **High-Performance API** - Built with FastAPI for maximum speed and efficiency
- **AI-Powered Conversations** - Integrated with OpenAI GPT for intelligent responses  
- **Real-time Chat** - WebSocket support for instant messaging
- **User Management** - Complete authentication and authorization system
- **Emotion Detection** - AI-powered emotion analysis using VADER and TextBlob
- **User Personalization** - Learning algorithms that adapt to user preferences

### 🛠 Technical Features
- **Database Integration** - PostgreSQL with SQLAlchemy ORM and Alembic migrations
- **Caching Layer** - Redis for improved performance and session management
- **Security First** - JWT authentication, CORS protection, and input validation
- **Auto-Generated Docs** - Interactive API documentation with Swagger UI
- **Docker Ready** - Containerized for easy deployment and development
- **Comprehensive Logging** - Structured logging with configurable levels
- **Health Monitoring** - Built-in health checks and system metrics

### 📊 Advanced Features
- **Chat Management** - Full CRUD operations for conversations and messages
- **Token Usage Tracking** - Monitor and manage API usage costs
- **Context Management** - Intelligent conversation context handling
- **Message Types** - Support for text, images, files, audio, and video
- **User Preferences** - Customizable conversation styles and settings
- **Analytics Ready** - Built-in metrics and analytics collection

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7.0+
- Docker & Docker Compose
- OpenAI API Key

### Option 1: Automated Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/NikhilOO7/Gennie-Backend.git
cd Gennie-Backend

# Run automated setup
python setup_and_run.py --start
```

The setup script will automatically:
- ✅ Install all dependencies
- ✅ Start Docker services (PostgreSQL + Redis)
- ✅ Run database migrations
- ✅ Start the FastAPI server
- ✅ Verify all services are healthy

### Option 2: Manual Setup

```bash
# Clone and navigate
git clone https://github.com/NikhilOO7/Gennie-Backend.git
cd Gennie-Backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration (see Configuration section)

# Start services with Docker
docker-compose up -d

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Docker-Only Setup

```bash
git clone https://github.com/NikhilOO7/Gennie-Backend.git
cd Gennie-Backend

# Start all services including the API
docker-compose up -d

# The API will be available at http://localhost:8000
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Application Settings
SECRET_KEY=your-super-secret-key-change-in-production
APP_VERSION=2.0.0
ENVIRONMENT=development

# Database Configuration
DATABASE_URL=postgresql+asyncpg://chatbot_user:your_password@localhost:5432/chatbot_db

# Redis Configuration  
REDIS_URL=redis://localhost:6379/0

# OpenAI Configuration
OPENAI_API_KEY=sk-your-openai-api-key-here
# OPENAI_ORGANIZATION_ID=org-your-org-id  # Optional, only for organization accounts

# Security Settings
JWT_SECRET_KEY=your-jwt-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS Settings (for production)
ALLOWED_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]
ALLOWED_HOSTS=["localhost", "yourdomain.com"]

# Logging
LOG_LEVEL=INFO
```

### Required API Keys

1. **OpenAI API Key**: Get from [OpenAI Platform](https://platform.openai.com/account/api-keys)
2. **Secret Keys**: Generate secure random strings for JWT and app secrets

## 📚 API Documentation

Once running, access the interactive documentation:

- **📊 Swagger UI**: http://localhost:8000/docs
- **📖 ReDoc**: http://localhost:8000/redoc
- **🏥 Health Check**: http://localhost:8000/health

### Core Endpoints

#### Authentication
- `POST /api/v1/auth/register` - Register new user
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/refresh` - Refresh JWT token
- `POST /api/v1/auth/logout` - User logout

#### User Management
- `GET /api/v1/users/me` - Get current user profile
- `PUT /api/v1/users/me` - Update user profile
- `GET /api/v1/users/me/stats` - Get user statistics

#### Chat Management
- `GET /api/v1/chat` - List user's chats
- `POST /api/v1/chat` - Create new chat
- `GET /api/v1/chat/{chat_id}` - Get chat details
- `POST /api/v1/chat/{chat_id}/messages` - Send message

#### AI Conversation
- `POST /api/v1/ai/chat` - AI conversation endpoint
- `POST /api/v1/ai/analyze-emotion` - Emotion analysis
- `GET /api/v1/ai/personalization` - Get user preferences

#### WebSocket
- `WS /api/v1/ws/chat/{chat_id}` - Real-time chat connection

## 🧪 Testing

### Quick API Test

```bash
# 1. Register a test user
curl -X POST "http://localhost:8000/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "username": "testuser", 
    "password": "TestPassword123!",
    "first_name": "Test",
    "last_name": "User"
  }'

# 2. Login to get token
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email_or_username": "test@example.com",
    "password": "TestPassword123!"
  }'

# 3. Use token for AI chat (replace YOUR_TOKEN)
curl -X POST "http://localhost:8000/api/v1/ai/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"message": "Hello, AI!"}'
```

### Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2025-06-27T06:59:22.615925+00:00",
  "version": "2.0.0",
  "environment": "development",
  "checks": {
    "database": {"status": "healthy"},
    "redis": {"status": "healthy"},
    "openai": {"status": "healthy"},
    "emotion_service": {"status": "healthy"}
  }
}
```

### Running Test Suite

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html

# Run specific test categories
python -m pytest tests/unit/ -v          # Unit tests
python -m pytest tests/integration/ -v   # Integration tests
```

## 🏗 Architecture

### Project Structure
```
ai-chatbot-backend/
├── app/                    # Main application package
│   ├── main.py            # FastAPI application entry point
│   ├── config.py          # Configuration settings
│   ├── database.py        # Database connection and session
│   ├── models/            # SQLAlchemy models
│   │   ├── user.py        # User model
│   │   ├── chat.py        # Chat session model
│   │   ├── message.py     # Message model
│   │   ├── emotion.py     # Emotion analysis model
│   │   └── user_preference.py # User preferences model
│   ├── routers/           # API route handlers
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── users.py       # User management endpoints
│   │   ├── chat.py        # Chat management endpoints
│   │   ├── ai.py          # AI conversation endpoints
│   │   ├── websocket.py   # WebSocket handlers
│   │   └── health.py      # Health check endpoints
│   ├── services/          # Business logic services
│   │   ├── openai_service.py     # OpenAI integration
│   │   ├── emotion_service.py    # Emotion detection
│   │   ├── personalization.py   # User personalization
│   │   ├── prompt_service.py     # Prompt management
│   │   └── utils.py              # Utility functions
│   └── utils/             # Utility functions and helpers
├── alembic/               # Database migrations
├── tests/                 # Test suite
├── docker-compose.yml     # Docker services configuration
├── requirements.txt       # Python dependencies
├── alembic.ini           # Alembic configuration
└── README.md             # This file
```

### Technology Stack

- **Framework**: FastAPI 0.109+ (Python 3.11+)
- **Database**: PostgreSQL 15+ with SQLAlchemy ORM
- **Cache**: Redis 7.0+
- **AI Integration**: OpenAI GPT-3.5/GPT-4
- **Authentication**: JWT with passlib and bcrypt
- **Real-time**: WebSockets
- **Migrations**: Alembic
- **Containerization**: Docker & Docker Compose
- **Testing**: pytest with async support
- **Documentation**: Auto-generated with FastAPI

## 🔧 Development

### Development Server

```bash
# Start with auto-reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start with detailed logging  
uvicorn app.main:app --reload --log-level debug
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Check current migration
alembic current

# Rollback migration
alembic downgrade -1
```

### Code Quality

```bash
# Format code
black app/ tests/

# Sort imports
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

## 🚀 Deployment

### Production Environment

1. **Set environment variables**:
   ```env
   ENVIRONMENT=production
   SECRET_KEY=your-production-secret-key
   DATABASE_URL=your-production-db-url
   REDIS_URL=your-production-redis-url
   OPENAI_API_KEY=your-openai-key
   ```

2. **Use production ASGI server**:
   ```bash
   gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
   ```

3. **Set up reverse proxy** (nginx/traefik)

4. **Configure SSL/TLS certificates**

### Docker Production

```bash
# Build production image
docker build -t ai-chatbot-backend .

# Run with production settings
docker-compose -f docker-compose.prod.yml up -d
```

## 🔍 Troubleshooting

### Common Issues

#### 1. Migration Errors
```bash
# Reset migrations (development only)
rm alembic/versions/*.py
alembic revision --autogenerate -m "Fresh migration"
alembic upgrade head
```

#### 2. Database Connection Issues
```bash
# Check database health
curl http://localhost:8000/health

# Check Docker services
docker-compose ps
docker-compose logs postgres
```

#### 3. OpenAI API Issues
- Verify API key in `.env` file
- Check API key permissions
- Monitor usage limits

#### 4. Authentication Issues
- Check JWT secret configuration
- Verify token expiration settings
- Test with fresh tokens

### Logs and Monitoring

```bash
# View application logs
docker-compose logs app

# View all service logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f app
```

## 📈 Performance

### Optimization Tips

1. **Database**:
   - Use connection pooling
   - Add appropriate indexes
   - Monitor query performance

2. **Caching**:
   - Leverage Redis for session data
   - Cache frequent queries
   - Use HTTP caching headers

3. **AI Integration**:
   - Monitor token usage
   - Implement request queuing
   - Cache similar responses

## 🛡 Security

### Security Features

- JWT-based authentication
- Password hashing with bcrypt
- CORS protection
- Input validation with Pydantic
- SQL injection prevention
- Rate limiting ready

### Security Checklist

- [ ] Change default secret keys
- [ ] Use HTTPS in production
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Monitor API usage
- [ ] Regular security updates

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run the test suite
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: [API Docs](http://localhost:8000/docs)
- **Issues**: [GitHub Issues](https://github.com/NikhilOO7/Gennie-Backend/issues)
- **Discussions**: [GitHub Discussions](https://github.com/NikhilOO7/Gennie-Backend/discussions)

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**NikhilOO7**
- GitHub: [@NikhilOO7](https://github.com/NikhilOO7)
- Project: [Gennie-Backend](https://github.com/NikhilOO7/Gennie-Backend)

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the amazing web framework
- [OpenAI](https://openai.com/) for AI capabilities
- [SQLAlchemy](https://sqlalchemy.org/) for database ORM
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
- [Alembic](https://alembic.sqlalchemy.org/) for database migrations

---

<div align="center">

**Built with ❤️ using FastAPI and OpenAI**

[⭐ Star this repository](https://github.com/NikhilOO7/Gennie-Backend) if you find it helpful!

</div>