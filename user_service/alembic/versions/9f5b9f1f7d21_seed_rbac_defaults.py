"""seed rbac defaults

Revision ID: 9f5b9f1f7d21
Revises: b2ab25ab7ac4
Create Date: 2026-05-05 17:10:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9f5b9f1f7d21"
down_revision: Union[str, Sequence[str], None] = "b2ab25ab7ac4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO roles (name, description)
            VALUES
                ('customer', 'Customer role'),
                ('seller', 'Seller role'),
                ('support', 'Support role'),
                ('admin', 'Admin role')
            ON CONFLICT (name) DO NOTHING
            """
        )
    )
    op.execute(
        sa.text(
            """
            INSERT INTO permissions (name, description)
            VALUES
                ('users:read_self', 'Read own user profile.'),
                ('users:update_self', 'Update own user profile.'),
                ('addresses:read_self', 'Read own saved addresses.'),
                ('addresses:write_self', 'Create, update, and delete own addresses.'),
                ('users:manage_roles', 'Assign and revoke user roles.')
            ON CONFLICT (name) DO NOTHING
            """
        )
    )

    # Customer baseline permissions.
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            JOIN permissions p ON p.name IN (
                'users:read_self',
                'users:update_self',
                'addresses:read_self',
                'addresses:write_self'
            )
            WHERE r.name = 'customer'
            ON CONFLICT DO NOTHING
            """
        )
    )

    # Seller starts with the same baseline as customer.
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            JOIN permissions p ON p.name IN (
                'users:read_self',
                'users:update_self',
                'addresses:read_self',
                'addresses:write_self'
            )
            WHERE r.name = 'seller'
            ON CONFLICT DO NOTHING
            """
        )
    )

    # Support can read user profiles (expand later as needed).
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            JOIN permissions p ON p.name = 'users:read_self'
            WHERE r.name = 'support'
            ON CONFLICT DO NOTHING
            """
        )
    )

    # Admin gets all defined permissions.
    op.execute(
        sa.text(
            """
            INSERT INTO role_permissions (role_id, permission_id)
            SELECT r.id, p.id
            FROM roles r
            CROSS JOIN permissions p
            WHERE r.name = 'admin'
            ON CONFLICT DO NOTHING
            """
        )
    )

    # Backfill existing users with customer role.
    op.execute(
        sa.text(
            """
            INSERT INTO user_roles (user_id, role_id)
            SELECT u.id, r.id
            FROM users u
            CROSS JOIN roles r
            WHERE r.name = 'customer'
            ON CONFLICT DO NOTHING
            """
        )
    )


def downgrade() -> None:
    op.execute(
        sa.text(
            """
            DELETE FROM user_roles
            WHERE role_id IN (SELECT id FROM roles WHERE name IN ('customer', 'seller', 'support', 'admin'))
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM role_permissions
            WHERE role_id IN (SELECT id FROM roles WHERE name IN ('customer', 'seller', 'support', 'admin'))
               OR permission_id IN (
                    SELECT id
                    FROM permissions
                    WHERE name IN (
                        'users:read_self',
                        'users:update_self',
                        'addresses:read_self',
                        'addresses:write_self',
                        'users:manage_roles'
                    )
               )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM permissions
            WHERE name IN (
                'users:read_self',
                'users:update_self',
                'addresses:read_self',
                'addresses:write_self',
                'users:manage_roles'
            )
            """
        )
    )
    op.execute(
        sa.text(
            """
            DELETE FROM roles
            WHERE name IN ('customer', 'seller', 'support', 'admin')
            """
        )
    )
