"""Kurs und Währung in daily_scores

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-04
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("daily_scores") as batch_op:
        batch_op.add_column(sa.Column("close_price", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("currency",    sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("daily_scores") as batch_op:
        batch_op.drop_column("currency")
        batch_op.drop_column("close_price")
