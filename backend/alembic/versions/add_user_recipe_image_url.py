"""add user_recipe image_url

Revision ID: a1b2c3d4e5f6
Revises: fd0e4a77df67
Create Date: 2026-03-07

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "fd0e4a77df67"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_recipes", sa.Column("image_url", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_recipes", "image_url")
