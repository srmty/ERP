"""Add default_unit column to item table

Revision ID: add_default_unit_to_item
Revises: bcc46779c341
Create Date: 2025-05-13 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'add_default_unit_to_item'
down_revision = 'bcc46779c341'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('item', sa.Column('default_unit', sa.String(length=32), nullable=True))

def downgrade():
    op.drop_column('item', 'default_unit') 