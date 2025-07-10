"""initial_tables_already_exist

Revision ID: 5578f8b9db9f
Revises: 793e27aceba8
Create Date: 2025-07-10 18:22:48.227309

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5578f8b9db9f'
down_revision: Union[str, None] = '793e27aceba8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    pass

def downgrade() -> None:
    pass
