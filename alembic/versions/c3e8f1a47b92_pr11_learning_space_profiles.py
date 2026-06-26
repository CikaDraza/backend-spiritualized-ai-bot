"""PR11.3: learning_space_profiles (Layer 2 memory)

Revision ID: c3e8f1a47b92
Revises: b2d7c9a14f30
Create Date: 2026-06-26 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c3e8f1a47b92'
down_revision: Union[str, Sequence[str], None] = 'b2d7c9a14f30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'learning_space_profiles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('space_id', sa.Integer(), nullable=False),
        sa.Column(
            'pillar_scores', postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"), nullable=False,
        ),
        sa.Column(
            'weak_areas', postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"), nullable=False,
        ),
        sa.Column(
            'domain_vocabulary', postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"), nullable=False,
        ),
        sa.Column('sessions_completed', sa.Integer(), server_default=sa.text('0'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['space_id'], ['learning_spaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'space_id', name='uq_space_profile_user_space'),
    )
    op.create_index(
        op.f('ix_learning_space_profiles_id'), 'learning_space_profiles', ['id'], unique=False
    )
    op.create_index(
        op.f('ix_learning_space_profiles_user_id'),
        'learning_space_profiles', ['user_id'], unique=False,
    )
    op.create_index(
        op.f('ix_learning_space_profiles_space_id'),
        'learning_space_profiles', ['space_id'], unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_learning_space_profiles_space_id'), table_name='learning_space_profiles')
    op.drop_index(op.f('ix_learning_space_profiles_user_id'), table_name='learning_space_profiles')
    op.drop_index(op.f('ix_learning_space_profiles_id'), table_name='learning_space_profiles')
    op.drop_table('learning_space_profiles')
