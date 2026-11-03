"""add incident source_id for durable idempotency

Revision ID: e4a71b83d910
Revises: dac68586f9c0
Create Date: 2026-11-03 16:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e4a71b83d910'
down_revision: Union[str, None] = 'dac68586f9c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('incidents', sa.Column('source_id', sa.String(length=255), nullable=True))
    op.create_index(op.f('ix_incidents_source_id'), 'incidents', ['source_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_incidents_source_id'), table_name='incidents')
    op.drop_column('incidents', 'source_id')

