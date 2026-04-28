"""add user profile fields and addresses table

Revision ID: d6c27187122b
Revises: 304c5d5341ec
Create Date: 2026-04-28 18:58:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd6c27187122b'
down_revision: Union[str, Sequence[str], None] = '304c5d5341ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('addresses',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('street', sa.String(), nullable=True),
        sa.Column('city', sa.String(), nullable=False),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('zip_code', sa.String(), nullable=False),
        sa.Column('country', sa.String(), nullable=False),
        sa.Column('is_default', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_addresses_id'), 'addresses', ['id'], unique=False)

    op.add_column('users', sa.Column('first_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('last_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('phone_number', sa.String(), nullable=True))
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=True))
    op.create_index(op.f('ix_users_phone_number'), 'users', ['phone_number'], unique=True)

    op.alter_column('users', 'created_at',
        existing_type=sa.String(),
        type_=sa.DateTime(),
        postgresql_using='created_at::timestamp without time zone'
    )
    op.alter_column('users', 'updated_at',
        existing_type=sa.String(),
        type_=sa.DateTime(),
        postgresql_using='updated_at::timestamp without time zone'
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column('users', 'updated_at',
        existing_type=sa.DateTime(),
        type_=sa.String()
    )
    op.alter_column('users', 'created_at',
        existing_type=sa.DateTime(),
        type_=sa.String()
    )

    op.drop_index(op.f('ix_users_phone_number'), table_name='users')
    op.drop_column('users', 'is_verified')
    op.drop_column('users', 'phone_number')
    op.drop_column('users', 'last_name')
    op.drop_column('users', 'first_name')

    op.drop_index(op.f('ix_addresses_id'), table_name='addresses')
    op.drop_table('addresses')
