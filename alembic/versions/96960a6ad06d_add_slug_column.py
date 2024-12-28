"""add slug column for clean urls

Revision ID: 96960a6ad06d
Revises: 7b97dc3e8e4c
Create Date: 2024-03-15 ...

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '96960a6ad06d'
down_revision: Union[str, None] = '7b97dc3e8e4c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new slug column
    op.add_column('messages', sa.Column('slug', sa.String(), nullable=True))
    # Create index for performance
    op.create_index('ix_messages_slug', 'messages', ['slug'], unique=False)

    # Copy existing slugs from hash to new slug column
    op.execute("""
        UPDATE messages 
        SET slug = hash 
        WHERE hash IS NOT NULL
    """)


def downgrade() -> None:
    # Remove index first
    op.drop_index('ix_messages_slug', table_name='messages')
    # Then remove column
    op.drop_column('messages', 'slug')
