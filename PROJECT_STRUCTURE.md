# AI Chatbot Backend - Project Structure

## Directory Structure

```
ai-chatbot-backend/
├── app/                          # Main application package
│   ├── __init__.py
│   ├── main.py                   # FastAPI application entry point
│   ├── api/                      # API related code
│   │   ├── __init__.py
│   │   └── v1/                   # API version 1
│   │       ├── __init__.py
│   │       ├── api.py            # API route aggregation
│   │       └── endpoints/        # Individual endpoint modules
│   │           ├── __init__.py
│   │           ├── health.py     # Health check endpoints
│   │           ├── chat.py       # Chat management endpoints
│   │           └── ai.py         # AI conversation endpoints
│   ├── core/                     # Core functionality
│   │   ├── __init__.py
│   │   ├── config.py            # Configuration settings
│   │   ├── database.py          # Database setup and connections
│   │   └── security.py          # Security utilities (future)
│   ├── models/                   # Database models
│   │   ├── __init__.py
│   │   ├── user.py              # User model
│   │   ├── chat.py              # Chat and Message models
│   │   └── user_preference.py   # User preferences model
│   ├── services/                 # Business logic services
│   │   ├── __init__.py
│   │   ├── openai_service.py    # OpenAI integration
│   │   ├── prompt_service.py    # Prompt engineering
│   │   └── emotion_service.py   # Emotion detection (future)
│   ├── utils/                    # Utility functions
│   │   ├── __init__.py
│   │   └── helpers.py           # Helper functions
│   └── schemas.py               # Pydantic models
├── tests/                        # Test files
│   ├── __init__.py
│   ├── unit/                    # Unit tests
│   │   └── __init__.py
│   └── integration/             # Integration tests
│       └── __init__.py
├── scripts/                      # Utility scripts
├── docs/                        # Documentation
├── alembic/                     # Database migrations
├── docker-compose.yml           # Docker services
├── Dockerfile                   # Application container
├── requirements.txt             # Python dependencies
├── .env.example                # Environment variables template
├── .gitignore                  # Git ignore rules
├── README.md                   # Project documentation
└── PROJECT_STRUCTURE.md        # This file
```

## Key Principles

1. **Separation of Concerns**: Each module has a specific responsibility
2. **API Versioning**: Supports future API versions through v1, v2, etc.
3. **Service Layer**: Business logic separated from API endpoints
4. **Clean Dependencies**: Models, services, and utilities properly isolated
5. **Testing Structure**: Unit and integration tests separated
6. **Configuration Management**: Centralized configuration in core/config.py

## File Naming Conventions

- **Models**: Singular nouns (user.py, chat.py)
- **Services**: Descriptive with _service suffix (openai_service.py)
- **Endpoints**: Match the resource name (chat.py for chat endpoints)
- **Tests**: Match the module being tested with test_ prefix

## Import Guidelines

- Use absolute imports from app root
- Keep circular imports minimal
- Import services in endpoints, not models in services
