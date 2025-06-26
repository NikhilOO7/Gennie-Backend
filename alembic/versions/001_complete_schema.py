"""Complete schema migration for AI Chatbot

Revision ID: 001_complete_schema
Revises: 
Create Date: 2025-06-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_complete_schema'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    """Complete database schema creation"""
    
    # Create users table if it doesn't exist
    op.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email VARCHAR(255) UNIQUE NOT NULL,
            username VARCHAR(50) UNIQUE NOT NULL,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT TRUE
        );
    """)
    
    # Add all missing columns to users table
    op.execute("""
        DO $$ 
        BEGIN
            -- Add password_hash column if it doesn't exist
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'password_hash'
            ) THEN
                ALTER TABLE users ADD COLUMN password_hash VARCHAR(255);
            END IF;
            
            -- Add profile columns
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'first_name') THEN
                ALTER TABLE users ADD COLUMN first_name VARCHAR(100);
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_name') THEN
                ALTER TABLE users ADD COLUMN last_name VARCHAR(100);
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'full_name') THEN
                ALTER TABLE users ADD COLUMN full_name VARCHAR(255);
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'avatar_url') THEN
                ALTER TABLE users ADD COLUMN avatar_url VARCHAR(500);
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'bio') THEN
                ALTER TABLE users ADD COLUMN bio TEXT;
            END IF;
            
            -- Add status columns
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'is_verified') THEN
                ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT FALSE;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'is_premium') THEN
                ALTER TABLE users ADD COLUMN is_premium BOOLEAN DEFAULT FALSE;
            END IF;
            
            -- Add preference columns
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'timezone') THEN
                ALTER TABLE users ADD COLUMN timezone VARCHAR(50) DEFAULT 'UTC';
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'language') THEN
                ALTER TABLE users ADD COLUMN language VARCHAR(10) DEFAULT 'en';
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'theme') THEN
                ALTER TABLE users ADD COLUMN theme VARCHAR(20) DEFAULT 'light';
            END IF;
            
            -- Add usage statistics
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'total_chats') THEN
                ALTER TABLE users ADD COLUMN total_chats INTEGER DEFAULT 0;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'total_messages') THEN
                ALTER TABLE users ADD COLUMN total_messages INTEGER DEFAULT 0;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'total_tokens_used') THEN
                ALTER TABLE users ADD COLUMN total_tokens_used INTEGER DEFAULT 0;
            END IF;
            
            -- Add settings column
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'settings') THEN
                ALTER TABLE users ADD COLUMN settings JSONB;
            END IF;
            
            -- Add timestamp columns
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'updated_at') THEN
                ALTER TABLE users ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_login') THEN
                ALTER TABLE users ADD COLUMN last_login TIMESTAMP WITH TIME ZONE;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'last_activity') THEN
                ALTER TABLE users ADD COLUMN last_activity TIMESTAMP WITH TIME ZONE;
            END IF;
            
            -- Add verification columns
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'email_verified_at') THEN
                ALTER TABLE users ADD COLUMN email_verified_at TIMESTAMP WITH TIME ZONE;
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'verification_token') THEN
                ALTER TABLE users ADD COLUMN verification_token VARCHAR(255);
            END IF;
            
            -- Add password reset columns
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'reset_token') THEN
                ALTER TABLE users ADD COLUMN reset_token VARCHAR(255);
            END IF;
            
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'reset_token_expires') THEN
                ALTER TABLE users ADD COLUMN reset_token_expires TIMESTAMP WITH TIME ZONE;
            END IF;
            
        END $$;
    """)
    
    # Update password_hash to be NOT NULL with default value for existing records
    op.execute("""
        UPDATE users SET password_hash = 'temp_hash_to_be_updated' WHERE password_hash IS NULL;
        ALTER TABLE users ALTER COLUMN password_hash SET NOT NULL;
    """)
    
    # Create chats table
    op.execute("""
        CREATE TABLE IF NOT EXISTS chats (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title VARCHAR(255),
            ai_model VARCHAR(50) DEFAULT 'gpt-3.5-turbo',
            system_prompt TEXT,
            is_archived BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            total_messages INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            settings JSONB
        );
    """)
    
    # Create messages table
    op.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id SERIAL PRIMARY KEY,
            chat_id INTEGER NOT NULL REFERENCES chats(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            sender_type VARCHAR(20) NOT NULL CHECK (sender_type IN ('user', 'assistant')),
            message_metadata JSONB,
            timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            edited_at TIMESTAMP WITH TIME ZONE,
            tokens_used INTEGER DEFAULT 0,
            processing_time FLOAT,
            is_deleted BOOLEAN DEFAULT FALSE
        );
    """)
    
    # Create emotions table
    op.execute("""
        CREATE TABLE IF NOT EXISTS emotions (
            id SERIAL PRIMARY KEY,
            message_id INTEGER NOT NULL REFERENCES messages(id) ON DELETE CASCADE,
            emotion_type VARCHAR(50) NOT NULL,
            confidence FLOAT NOT NULL,
            details JSONB,
            analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Create user_preferences table
    op.execute("""
        CREATE TABLE IF NOT EXISTS user_preferences (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            interests TEXT[],
            preferred_topics TEXT[],
            avoided_topics TEXT[],
            communication_style VARCHAR(50) DEFAULT 'casual',
            response_style VARCHAR(50) DEFAULT 'balanced',
            ai_personality VARCHAR(50) DEFAULT 'helpful',
            preferred_response_length VARCHAR(20) DEFAULT 'medium',
            notification_settings JSONB,
            privacy_settings JSONB,
            learning_enabled BOOLEAN DEFAULT TRUE,
            personalization_level VARCHAR(20) DEFAULT 'medium',
            most_active_hours JSONB,
            preferred_conversation_length INTEGER,
            typical_session_duration INTEGER,
            expertise_level JSONB,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
    """)
    
    # Create indexes for better performance
    op.execute("""
        CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
        CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
        CREATE INDEX IF NOT EXISTS idx_chats_user_id ON chats(user_id);
        CREATE INDEX IF NOT EXISTS idx_chats_created_at ON chats(created_at);
        CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);
        CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
        CREATE INDEX IF NOT EXISTS idx_emotions_message_id ON emotions(message_id);
        CREATE INDEX IF NOT EXISTS idx_user_preferences_user_id ON user_preferences(user_id);
    """)

def downgrade():
    """Drop all tables"""
    op.execute("DROP TABLE IF EXISTS user_preferences CASCADE;")
    op.execute("DROP TABLE IF EXISTS emotions CASCADE;")
    op.execute("DROP TABLE IF EXISTS messages CASCADE;")
    op.execute("DROP TABLE IF EXISTS chats CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")