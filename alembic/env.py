"""Alembic environment configuration."""

import os
import sys
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add your project directory to Python path
current_path = os.path.dirname(os.path.abspath(__file__))
parent_path = os.path.dirname(current_path)
sys.path.insert(0, parent_path)

# Import your models
try:
    from app.database import Base
    from app.models import User, Chat, Message, Emotion, UserPreferences
    print("✅ Successfully imported all models")
except ImportError as e:
    print(f"❌ Failed to import models: {e}")
    print("Current working directory:", os.getcwd())
    print("Python path:", sys.path)
    raise

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Get database URL from environment variable
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)
    print(f"✅ Using database URL from environment")
else:
    print("❌ DATABASE_URL not found in environment variables")
    raise ValueError("DATABASE_URL environment variable is required")

# Set target metadata for autogenerate support
target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    print("🔄 Running migrations in offline mode")
    run_migrations_offline()
else:
    print("🔄 Running migrations in online mode")
    run_migrations_online()
