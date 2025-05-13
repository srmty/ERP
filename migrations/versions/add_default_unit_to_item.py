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
    with op.batch_alter_table('item', schema=None) as batch_op:
        batch_op.add_column(sa.Column('default_unit', sa.String(length=32), nullable=True))

def downgrade():
    with op.batch_alter_table('item', schema=None) as batch_op:
        batch_op.drop_column('default_unit') 