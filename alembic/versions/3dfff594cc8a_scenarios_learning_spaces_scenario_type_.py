"""scenarios -> learning_spaces (scenario_type/level/persona)

Revision ID: 3dfff594cc8a
Revises: a1cf86800621
Create Date: 2026-06-08 05:39:15.642594

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3dfff594cc8a'
down_revision: Union[str, Sequence[str], None] = 'a1cf86800621'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SCENARIO_TYPES = ("business_communication", "everyday_conversation", "job_interview", "shopping", "travel")
LEVELS = ("A1", "A2", "B1", "B2", "C1")
PERSONAS = ("mila", "viktor", "nora", "maria")


def upgrade() -> None:
    """Evolve the per-user `scenarios` table into `learning_spaces`."""
    bind = op.get_bind()

    # 1. enum types
    space_scenario_type = sa.Enum(*SCENARIO_TYPES, name="space_scenario_type")
    space_level = sa.Enum(*LEVELS, name="space_level")
    space_persona = sa.Enum(*PERSONAS, name="space_persona")
    space_scenario_type.create(bind, checkfirst=True)
    space_level.create(bind, checkfirst=True)
    space_persona.create(bind, checkfirst=True)

    # 2. rename the table (FKs from test_slots/transcripts auto-follow in Postgres)
    op.rename_table("scenarios", "learning_spaces")
    op.execute("ALTER INDEX ix_scenarios_id RENAME TO ix_learning_spaces_id")
    op.execute("ALTER INDEX ix_scenarios_user_id RENAME TO ix_learning_spaces_user_id")

    # 3. drop the old free-text description
    op.drop_column("learning_spaces", "description")

    # 4. add the new columns; server_default backfills existing rows, then drop the default
    #    (the app always supplies these on create).
    op.add_column(
        "learning_spaces",
        sa.Column(
            "scenario_type",
            sa.Enum(*SCENARIO_TYPES, name="space_scenario_type", create_type=False),
            nullable=False,
            server_default="everyday_conversation",
        ),
    )
    op.add_column(
        "learning_spaces",
        sa.Column(
            "level",
            sa.Enum(*LEVELS, name="space_level", create_type=False),
            nullable=False,
            server_default="A1",
        ),
    )
    op.add_column(
        "learning_spaces",
        sa.Column(
            "persona",
            sa.Enum(*PERSONAS, name="space_persona", create_type=False),
            nullable=False,
            server_default="viktor",
        ),
    )
    op.alter_column("learning_spaces", "scenario_type", server_default=None)
    op.alter_column("learning_spaces", "level", server_default=None)
    op.alter_column("learning_spaces", "persona", server_default=None)


def downgrade() -> None:
    """Reverse: learning_spaces -> scenarios."""
    op.add_column("learning_spaces", sa.Column("description", sa.Text(), nullable=True))
    op.drop_column("learning_spaces", "persona")
    op.drop_column("learning_spaces", "level")
    op.drop_column("learning_spaces", "scenario_type")
    op.execute("ALTER INDEX ix_learning_spaces_user_id RENAME TO ix_scenarios_user_id")
    op.execute("ALTER INDEX ix_learning_spaces_id RENAME TO ix_scenarios_id")
    op.rename_table("learning_spaces", "scenarios")
    sa.Enum(name="space_persona").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="space_level").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="space_scenario_type").drop(op.get_bind(), checkfirst=True)
