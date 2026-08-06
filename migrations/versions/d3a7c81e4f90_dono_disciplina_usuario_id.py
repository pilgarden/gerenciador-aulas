"""dono da disciplina (usuario_id)

Revision ID: d3a7c81e4f90
Revises: c2f8d91a0b12
Create Date: 2026-08-05 22:50:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "d3a7c81e4f90"
down_revision = "c2f8d91a0b12"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("disciplinas", schema=None) as batch_op:
        batch_op.add_column(sa.Column("usuario_id", sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f("ix_disciplinas_usuario_id"), ["usuario_id"], unique=False)
        batch_op.create_foreign_key(
            "fk_disciplinas_usuario_id",
            "usuarios",
            ["usuario_id"],
            ["id"],
        )

    conn = op.get_bind()
    admin_id = conn.execute(
        sa.text("SELECT id FROM usuarios WHERE papel = 'admin' ORDER BY id LIMIT 1")
    ).scalar()
    if admin_id is None:
        admin_id = conn.execute(sa.text("SELECT id FROM usuarios ORDER BY id LIMIT 1")).scalar()
    if admin_id is not None:
        conn.execute(
            sa.text("UPDATE disciplinas SET usuario_id = :uid WHERE usuario_id IS NULL"),
            {"uid": admin_id},
        )

    with op.batch_alter_table("disciplinas", schema=None) as batch_op:
        batch_op.alter_column("usuario_id", existing_type=sa.Integer(), nullable=False)
        batch_op.drop_constraint("uq_disciplina_semestre_codigo_turma", type_="unique")
        batch_op.create_unique_constraint(
            "uq_disciplina_usuario_semestre_codigo_turma",
            ["usuario_id", "semestre_id", "codigo", "turma"],
        )


def downgrade():
    with op.batch_alter_table("disciplinas", schema=None) as batch_op:
        batch_op.drop_constraint("uq_disciplina_usuario_semestre_codigo_turma", type_="unique")
        batch_op.create_unique_constraint(
            "uq_disciplina_semestre_codigo_turma",
            ["semestre_id", "codigo", "turma"],
        )
        batch_op.drop_constraint("fk_disciplinas_usuario_id", type_="foreignkey")
        batch_op.drop_index(batch_op.f("ix_disciplinas_usuario_id"))
        batch_op.drop_column("usuario_id")
