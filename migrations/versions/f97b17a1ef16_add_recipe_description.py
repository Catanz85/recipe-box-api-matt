"""Add recipe description

Revision ID: f97b17a1ef16
Revises: 8f03b8b6fe1c
Create Date: 2026-11-27 15:12:58.701140

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f97b17a1ef16'
down_revision = '8f03b8b6fe1c'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "recipes",
        sa.Column(
            "description",
            sa.Text(),
            server_default=sa.text("''"),
            nullable=False
        )
    )


def downgrade():
    op.drop_column("recipes", "description")
