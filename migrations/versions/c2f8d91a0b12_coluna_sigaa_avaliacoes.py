"""Adiciona coluna_sigaa às avaliações."""
from alembic import op
import sqlalchemy as sa


revision = "c2f8d91a0b12"
down_revision = "b6e1a15ba443"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("avaliacoes", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("coluna_sigaa", sa.String(length=20), nullable=False, server_default="Unid. 1")
        )

    connection = op.get_bind()
    inspector = sa.inspect(connection)
    if "avaliacoes" not in inspector.get_table_names():
        return

    rows = connection.execute(sa.text("SELECT id, nome FROM avaliacoes")).fetchall()
    for row in rows:
        nome = (row[1] or "").strip().lower()
        if nome in ("rec.", "rec") or nome.startswith("rec"):
            coluna = "Rec."
        elif "2" in nome and "unid" in nome:
            coluna = "Unid. 2"
        elif nome in ("unid. 2", "unid 2", "unid.2"):
            coluna = "Unid. 2"
        else:
            coluna = "Unid. 1"
        connection.execute(
            sa.text("UPDATE avaliacoes SET coluna_sigaa = :coluna WHERE id = :id"),
            {"coluna": coluna, "id": row[0]},
        )


def downgrade():
    with op.batch_alter_table("avaliacoes", schema=None) as batch_op:
        batch_op.drop_column("coluna_sigaa")
