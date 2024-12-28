"""add_is_private_column

Revision ID: ac09247fad7a
Revises: 96960a6ad06d
Create Date: 2024-12-29 00:03:02.114661

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ac09247fad7a'
down_revision: Union[str, None] = '96960a6ad06d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add column as nullable first
    op.add_column('messages', sa.Column('is_private', sa.Boolean(), nullable=True))
    
    # 2. Set default value for existing records
    op.execute("UPDATE messages SET is_private = FALSE WHERE is_private IS NULL")
    
    # 3. Make it non-nullable with a default
    op.alter_column('messages', 'is_private',
        existing_type=sa.Boolean(),
        nullable=False,
        server_default='false'  # This sets default for future inserts
    )


def downgrade() -> None:
    op.drop_column('messages', 'is_private')
