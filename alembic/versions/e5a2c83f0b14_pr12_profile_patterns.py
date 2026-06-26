"""PR12: learning_profiles.recommendations + patterns (pattern detection)

Revision ID: e5a2c83f0b14
Revises: d4f1b6e29a07
Create Date: 2026-06-27 09:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'e5a2c83f0b14'
down_revision: Union[str, Sequence[str], None] = 'd4f1b6e29a07'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'learning_profiles',
        sa.Column('recommendations', postgresql.JSONB(astext_type=sa.Text()),
                  server_default=sa.text("'[]'::jsonb"), nullable=False),
    )
    op.add_column(
        'learning_profiles',
        sa.Column('patterns', postgresql.JSONB(astext_type=sa.Text()),
                  server_default=sa.text("'{}'::jsonb"), nullable=False),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('learning_profiles', 'patterns')
    op.drop_column('learning_profiles', 'recommendations')
