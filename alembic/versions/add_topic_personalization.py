"""Add related_topic and chat_mode columns to chats table

Revision ID: add_missing_chat_columns
Revises: 
Create Date: 2025-07-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_missing_chat_columns'
down_revision = '5578f8b9db9f'  # Update this with your latest migration revision ID
branch_labels = None
depends_on = None


def upgrade():
    """Add missing columns to chats table"""
    # Add chat_mode column with default value 'text'
    op.add_column('chats', 
        sa.Column('chat_mode', sa.String(20), nullable=False, server_default='text')
    )
    
    # Add related_topic column (nullable)
    op.add_column('chats', 
        sa.Column('related_topic', sa.String(50), nullable=True)
    )
    
    # Create index on related_topic for better performance
    op.create_index('idx_chat_topic', 'chats', ['related_topic'])
    
    # Remove server default after adding the column
    op.alter_column('chats', 'chat_mode', server_default=None)


def downgrade():
    """Remove the added columns"""
    # Drop the index first
    op.drop_index('idx_chat_topic', 'chats')
    
    # Drop the columns
    op.drop_column('chats', 'related_topic')
    op.drop_column('chats', 'chat_mode')