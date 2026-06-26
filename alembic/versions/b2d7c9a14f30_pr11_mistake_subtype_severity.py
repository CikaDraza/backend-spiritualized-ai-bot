"""PR11.2: add mistakes.subtype + mistakes.severity (learning events)

Revision ID: b2d7c9a14f30
Revises: 3dfff594cc8a
Create Date: 2026-06-26 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2d7c9a14f30'
down_revision: Union[str, Sequence[str], None] = '3dfff594cc8a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_SUBTYPES = (
    'articles', 'prepositions', 'verb_tenses', 'word_order', 'vocabulary',
    'clarity', 'spelling', 'pronunciation', 'idioms', 'naturalness', 'other',
)
_SEVERITIES = ('minor', 'moderate', 'major')


def upgrade() -> None:
    """Upgrade schema."""
    # add_column does NOT auto-create enum types — create them first.
    subtype_enum = sa.Enum(*_SUBTYPES, name='mistake_subtype')
    severity_enum = sa.Enum(*_SEVERITIES, name='mistake_severity')
    subtype_enum.create(op.get_bind(), checkfirst=True)
    severity_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'mistakes',
        sa.Column(
            'subtype',
            sa.Enum(*_SUBTYPES, name='mistake_subtype', create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        'mistakes',
        sa.Column(
            'severity',
            sa.Enum(*_SEVERITIES, name='mistake_severity', create_type=False),
            nullable=True,
        ),
    )
    op.create_index(op.f('ix_mistakes_subtype'), 'mistakes', ['subtype'], unique=False)
    op.create_index(op.f('ix_mistakes_severity'), 'mistakes', ['severity'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_mistakes_severity'), table_name='mistakes')
    op.drop_index(op.f('ix_mistakes_subtype'), table_name='mistakes')
    op.drop_column('mistakes', 'severity')
    op.drop_column('mistakes', 'subtype')
    sa.Enum(name='mistake_severity').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='mistake_subtype').drop(op.get_bind(), checkfirst=True)
