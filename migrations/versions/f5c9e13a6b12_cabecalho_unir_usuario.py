"""campos de cabeçalho UNIR no usuário

Revision ID: f5c9e13a6b12
Revises: e4b8d02f5a01
Create Date: 2026-08-05 23:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "f5c9e13a6b12"
down_revision = "e4b8d02f5a01"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "acesso_cabecalho_unir",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            )
        )
        batch_op.add_column(
            sa.Column(
                "tratamento",
                sa.String(length=40),
                nullable=False,
                server_default="Prof.",
            )
        )


def downgrade():
    with op.batch_alter_table("usuarios", schema=None) as batch_op:
        batch_op.drop_column("tratamento")
        batch_op.drop_column("acesso_cabecalho_unir")
