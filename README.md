# 🤖 Chat Backend API

> A production-ready AI-powered conversational backend built with FastAPI, featuring real-time chat capabilities, OpenAI integration, and comprehensive user management.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-00a000?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat&logo=python)](https://python.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?style=flat&logo=postgresql)](https://postgresql.org)
[![Redis](https://img.shields.io/badge/Redis-7.0+-dc382d?style=flat&logo=redis)](https://redis.io)
[![OpenAI](https://img.shields.io/badge/OpenAI-API-412991?style=flat&logo=openai)](https://openai.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker)](https://docker.com)

## ✨ Features

- 🚀 **High-Performance API** - Built with FastAPI for maximum speed and efficiency
- 🤖 **AI-Powered Conversations** - Integrated with OpenAI GPT for intelligent responses
- 💬 **Real-time Chat** - WebSocket support for instant messaging
- 👥 **User Management** - Complete authentication and authorization system
- 🗄️ **Database Integration** - PostgreSQL with SQLAlchemy ORM
- ⚡ **Caching Layer** - Redis for improved performance
- 🐳 **Docker Ready** - Containerized for easy deployment
- 📊 **Database Migrations** - Alembic for version-controlled database changes
- 🔒 **Security First** - JWT authentication, CORS protection, and input validation
- 📖 **Auto-Generated Docs** - Interactive API documentation with Swagger UI

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7.0+
- Docker & Docker Compose (optional)

### Option 1: One-Command Setup (Recommended)

```bash
# Clone the repository
git clone https://github.com/NikhilOO7/chat-backend.git
cd chat-backend

# Development setup (installs dependencies, starts services, runs migrations)
python setup.py setup --env dev

# Start development server
python setup.py start --env dev
```

### Option 2: Manual Setup

```bash
# Clone and navigate
git clone https://github.com/NikhilOO7/chat-backend.git
cd chat-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Start services with Docker
docker-compose up -d

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload
```

### Option 3: Docker-Only Setup

```bash
git clone https://github.com/NikhilOO7/chat-backend.git
cd chat-backend

# Start all services including the API
docker-compose up -d

# The API will be available at http://localhost:8000
```

## 📁 Project Architecture

```
chat-backend/
├── 📁 app/                     # Application source code
│   ├── 📁 api/                # API layer
│   │   └── 📁 v1/            # API version 1
│   │       ├── api.py        # Main API router
│   │       └── 📁 endpoints/ # Individual endpoint modules
│   │           ├── ai.py     # AI chat endpoints
│   │           ├── auth.py   # Authentication endpoints
│   │           ├── chat.py   # Chat management endpoints
│   │           └── health.py # Health check endpoints
│   ├── 📁 core/              # Core functionality
│   │   ├── config.py         # Configuration management
│   │   └── database.py       # Database connection setup
│   ├── 📁 models/            # Database models (SQLAlchemy)
│   │   ├── user.py           # User model
│   │   ├── chat.py           # Chat model
│   │   └── user_preference.py # User preferences model
│   ├── 📁 services/          # Business logic layer
│   │   ├── openai_service.py # OpenAI integration
│   │   ├── prompt_service.py # Prompt engineering
│   │   └── utils.py          # Service utilities
│   ├── 📁 utils/             # Utility functions
│   ├── schemas.py            # Pydantic schemas for API
│   └── main.py               # FastAPI application entry point
├── 📁 alembic/               # Database migrations
├── 📁 tests/                 # Test suite
│   ├── 📁 unit/             # Unit tests
│   └── 📁 integration/      # Integration tests
├── 📁 setup/                 # Development & setup tools
├── 🐳 docker-compose.yml     # Multi-container Docker setup
├── 🐳 dockerfile            # Application container definition
├── 📋 requirements.txt       # Production dependencies
├── ⚙️ setup.py              # Master setup script
└── 📖 README.md             # This file
```

## 🛠️ Available Commands

The project includes a master `setup.py` script for easy management:

### Environment Setup
```bash
python setup.py setup --env dev     # Setup development environment
python setup.py setup --env prod    # Setup production environment
```

### Server Management
```bash
python setup.py start --env dev     # Start development server (with reload)
python setup.py start --env prod    # Start production server (with workers)
```

### Maintenance
```bash
python setup.py test                # Run complete test suite
python setup.py clean               # Clean project artifacts and cache
```

### Manual Commands
```bash
# Database operations
alembic upgrade head                 # Apply latest migrations
alembic revision --autogenerate -m "description"  # Create new migration

# Testing
pytest tests/                       # Run all tests
pytest tests/unit/                  # Run unit tests only
pytest tests/integration/           # Run integration tests only

# Code quality
black app/                          # Format code
isort app/                          # Sort imports
flake8 app/                         # Lint code
```

## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Database Configuration
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
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_MAX_TOKENS=1000

# Application Configuration
SECRET_KEY=your_super_secret_key_here_minimum_32_characters
DEBUG=False
ENVIRONMENT=production
API_V1_STR=/api/v1

# Security Configuration
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# CORS Configuration
CORS_ORIGINS=["http://localhost:3000", "https://yourdomain.com"]
CORS_CREDENTIALS=true
CORS_METHODS=["*"]
CORS_HEADERS=["*"]

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

### Docker Configuration

The project includes optimized Docker configurations:

- **Development**: `docker-compose.yml` with hot-reload
- **Production**: Multi-stage builds for smaller images

## 📖 API Documentation

Once the server is running, access the interactive API documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

### Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | User authentication |
| `/api/v1/auth/register` | POST | User registration |
| `/api/v1/chat/` | GET | List user chats |
| `/api/v1/chat/` | POST | Create new chat |
| `/api/v1/chat/{id}/messages` | GET | Get chat messages |
| `/api/v1/ai/chat` | POST | Send message to AI |
| `/api/v1/health` | GET | Health check |

## 🏗️ Architecture Overview

### Tech Stack

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Cache**: Redis for session management and caching
- **AI Provider**: OpenAI GPT-3.5/GPT-4
- **Authentication**: JWT tokens with refresh mechanism
- **Validation**: Pydantic for request/response validation
- **Migrations**: Alembic for database version control
- **Testing**: Pytest with async support
- **Containerization**: Docker with multi-stage builds

### Design Patterns

- **Repository Pattern**: Clean separation between data access and business logic
- **Service Layer**: Business logic abstracted from API endpoints
- **Dependency Injection**: FastAPI's built-in DI for database sessions, services
- **Schema Validation**: Pydantic models for type safety and validation
- **Error Handling**: Centralized exception handling with proper HTTP status codes

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python setup.py test

# Run with coverage
pytest --cov=app tests/

# Run specific test files
pytest tests/unit/test_auth.py
pytest tests/integration/test_chat_api.py

# Run tests with output
pytest -v -s tests/
```

### Test Structure

- **Unit Tests**: Test individual functions and classes
- **Integration Tests**: Test API endpoints and database interactions
- **Fixtures**: Shared test data and configurations
- **Mocking**: External services (OpenAI) are mocked in tests

## 🚀 Deployment

### Production Deployment

1. **Prepare Environment**:
   ```bash
   python setup.py setup --env prod
   ```

2. **Set Environment Variables**:
   - Copy `.env.example` to `.env`
   - Update with production values
   - Ensure SECRET_KEY is secure and unique

3. **Database Setup**:
   ```bash
   alembic upgrade head
   ```

4. **Start Production Server**:
   ```bash
   python setup.py start --env prod
   ```

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d

# Scale the API service
docker-compose up -d --scale api=3

# View logs
docker-compose logs -f api
```

### Cloud Deployment

The application is ready for deployment on:

- **AWS**: ECS, Lambda, or EC2
- **Google Cloud**: Cloud Run, GKE, or Compute Engine
- **Azure**: Container Instances or App Service
- **Heroku**: With Postgres and Redis add-ons
- **DigitalOcean**: App Platform or Droplets

### Environment-Specific Configurations

- **Development**: Debug mode, detailed logging, test database
- **Staging**: Production-like settings with test data
- **Production**: Optimized performance, security hardening, monitoring

## 🔒 Security Features

- **JWT Authentication**: Secure token-based authentication
- **Password Hashing**: bcrypt for secure password storage
- **CORS Protection**: Configurable cross-origin resource sharing
- **Rate Limiting**: Built-in request rate limiting
- **Input Validation**: Comprehensive request validation with Pydantic
- **SQL Injection Protection**: SQLAlchemy ORM prevents SQL injection
- **Environment Variables**: Sensitive data stored in environment variables

## 📊 Monitoring & Logging

### Built-in Health Checks

```bash
curl http://localhost:8000/api/v1/health
```

### Logging

The application includes structured logging:
- Request/response logging
- Error tracking and stack traces
- Performance metrics
- Database query logging (development only)

### Metrics

Key metrics to monitor:
- Response times
- Error rates
- Database connection pool
- Redis cache hit rates
- OpenAI API usage and costs

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Make your changes**
4. **Run tests**: `python setup.py test`
5. **Commit your changes**: `git commit -m 'Add amazing feature'`
6. **Push to the branch**: `git push origin feature/amazing-feature`
7. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guidelines
- Write tests for new features
- Update documentation as needed
- Use type hints
- Keep functions small and focused

### Code Quality

```bash
# Format code
black app/
isort app/

# Check linting
flake8 app/

# Type checking
mypy app/
```

## 📋 Changelog

### v1.0.0 (Current)
- ✅ Initial release
- ✅ FastAPI backend with OpenAI integration
- ✅ User authentication and chat management
- ✅ Docker containerization
- ✅ Comprehensive test suite
- ✅ Production-ready deployment

### Planned Features
- 🔄 WebSocket support for real-time chat
- 🔄 File upload and processing
- 🔄 Advanced AI conversation features
- 🔄 Analytics and usage tracking
- 🔄 Multi-language support

## 🆘 Troubleshooting

### Common Issues

1. **Database Connection Issues**:
   ```bash
   # Check if PostgreSQL is running
   docker-compose ps postgres
   
   # View database logs
   docker-compose logs postgres
   ```

2. **Redis Connection Issues**:
   ```bash
   # Check if Redis is running
   docker-compose ps redis
   
   # Test Redis connection
   redis-cli ping
   ```

3. **OpenAI API Issues**:
   - Verify API key in `.env` file
   - Check OpenAI API quota and billing
   - Monitor rate limits

4. **Import Errors**:
   ```bash
   # Ensure virtual environment is activated
   source venv/bin/activate
   
   # Reinstall dependencies
   pip install -r requirements.txt
   ```

### Getting Help

- 📧 **Issues**: Create an issue on GitHub
- 💬 **Discussions**: Use GitHub Discussions for questions
- 📖 **Documentation**: Check the `/docs` endpoint when server is running

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**NikhilOO7**
- GitHub: [@NikhilOO7](https://github.com/NikhilOO7)
- Project: [chat-backend](https://github.com/NikhilOO7/chat-backend)

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the amazing web framework
- [OpenAI](https://openai.com/) for AI capabilities
- [SQLAlchemy](https://sqlalchemy.org/) for database ORM
- [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
- [Alembic](https://alembic.sqlalchemy.org/) for database migrations

---

<div align="center">

**Built with ❤️ using FastAPI and OpenAI**

[⭐ Star this repository](https://github.com/NikhilOO7/chat-backend) if you find it helpful!

</div>