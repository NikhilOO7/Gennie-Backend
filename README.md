# Chat Backend API

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
