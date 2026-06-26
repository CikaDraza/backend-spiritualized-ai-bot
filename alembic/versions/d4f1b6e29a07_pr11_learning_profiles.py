"""PR11.4: learning_profiles (Layer 3 global profile + CEFR)

Revision ID: d4f1b6e29a07
Revises: c3e8f1a47b92
Create Date: 2026-06-26 22:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'd4f1b6e29a07'
down_revision: Union[str, Sequence[str], None] = 'c3e8f1a47b92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'learning_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('committed_cefr', sa.String(length=2), nullable=True),
        sa.Column('emerging_cefr', sa.String(length=2), nullable=True),
        sa.Column('target_cefr', sa.String(length=2), nullable=True),
        sa.Column('cefr_confidence', sa.Float(), server_default=sa.text('0'), nullable=False),
        sa.Column('cefr_history', postgresql.JSONB(astext_type=sa.Text()),
                  server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('strengths', postgresql.JSONB(astext_type=sa.Text()),
                  server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('weaknesses', postgresql.JSONB(astext_type=sa.Text()),
                  server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('frequent_mistakes', postgresql.JSONB(astext_type=sa.Text()),
                  server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('mastered', postgresql.JSONB(astext_type=sa.Text()),
                  server_default=sa.text("'[]'::jsonb"), nullable=False),
        sa.Column('learning_style', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('totals', postgresql.JSONB(astext_type=sa.Text()),
                  server_default=sa.text("'{}'::jsonb"), nullable=False),
        sa.Column('sessions_completed', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', name='uq_learning_profiles_user'),
    )
    op.create_index(op.f('ix_learning_profiles_id'), 'learning_profiles', ['id'], unique=False)
    op.create_index(
        op.f('ix_learning_profiles_user_id'), 'learning_profiles', ['user_id'], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_learning_profiles_user_id'), table_name='learning_profiles')
    op.drop_index(op.f('ix_learning_profiles_id'), table_name='learning_profiles')
    op.drop_table('learning_profiles')
