# AI Chatbot Backend - Project Structure

## Directory Layout
```
ai-chatbot-backend/
├── app/                    # Main application package
│   ├── __init__.py
│   ├── main.py            # FastAPI application entry point
│   ├── config.py          # Configuration settings
│   ├── database.py        # Database connection and session
│   ├── models/            # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── user.py        # User model
│   │   ├── chat.py        # Chat session model
│   │   ├── message.py     # Message model
│   │   ├── emotion.py     # Emotion analysis model
│   │   └── user_preferences.py # User preferences model
│   ├── routers/           # API route handlers
│   │   ├── __init__.py
│   │   ├── chat.py        # Chat management endpoints
│   │   ├── ai.py          # AI conversation endpoints
│   │   └── websocket.py   # WebSocket handlers
│   ├── services/          # Business logic services
│   │   ├── __init__.py
│   │   ├── openai_service.py     # OpenAI integration
│   │   ├── emotion_service.py    # Emotion detection
│   │   └── personalization.py   # User personalization
│   └── utils/             # Utility functions
│       └── __init__.py
├── alembic/               # Database migrations
│   ├── versions/          # Migration files
│   ├── env.py            # Alembic environment
│   └── script.py.mako    # Migration template
├── requirements.txt       # Python dependencies
├── alembic.ini           # Alembic configuration
├── .env                  # Environment variables (not in git)
├── .gitignore           # Git ignore patterns
├── docker-compose.yml   # Docker services (optional)
└── README.md           # Project documentation
```

## Key Files

### Core Application
- **app/main.py**: FastAPI app initialization, middleware, and router inclusion
- **app/config.py**: Environment-based configuration management
- **app/database.py**: SQLAlchemy engine, session, and Base class

### Database Models
- **models/user.py**: User authentication and profile data
- **models/chat.py**: Conversation sessions
- **models/message.py**: Individual chat messages
- **models/emotion.py**: Emotion analysis results
- **models/user_preferences.py**: User personalization data

### API Routes
- **routers/chat.py**: CRUD operations for chats and messages
- **routers/ai.py**: AI conversation endpoints
- **routers/websocket.py**: Real-time WebSocket communication

### Services
- **services/openai_service.py**: OpenAI API integration
- **services/emotion_service.py**: Emotion detection and analysis
- **services/personalization.py**: User behavior learning and adaptation

## Database Migrations
All database schema changes are managed through Alembic migrations in the `alembic/versions/` directory.

## Environment Configuration
The application uses environment variables for configuration. See `.env.example` for required variables.
