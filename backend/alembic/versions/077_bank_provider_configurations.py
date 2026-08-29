"""add user-owned bank provider configurations

Revision ID: 077
Revises: 076
Create Date: 2026-08-24

Existing bank connections intentionally retain a NULL configuration reference:
they keep using the deployment-wide environment credentials exactly as before.
Only connections created after a user saves a personal provider configuration
pin that configuration for future syncs.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "077"
down_revision: Union[str, None] = "076"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "bank_provider_configurations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("credentials_encrypted", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "provider", name="uq_bank_provider_configuration_user_provider"),
    )
    op.create_index(
        "ix_bank_provider_configurations_user_id",
        "bank_provider_configurations",
        ["user_id"],
    )
    op.add_column(
        "bank_connections",
        sa.Column("provider_configuration_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_bank_connections_provider_configuration_id",
        "bank_connections",
        "bank_provider_configurations",
        ["provider_configuration_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_bank_connections_provider_configuration_id",
        "bank_connections",
        ["provider_configuration_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_bank_connections_provider_configuration_id", table_name="bank_connections")
    op.drop_constraint("fk_bank_connections_provider_configuration_id", "bank_connections", type_="foreignkey")
    op.drop_column("bank_connections", "provider_configuration_id")
    op.drop_index("ix_bank_provider_configurations_user_id", table_name="bank_provider_configurations")
    op.drop_table("bank_provider_configurations")
