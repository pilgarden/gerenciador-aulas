"""dono, colaboradores, em_grupo e grupos de alunos

Revision ID: e4b8d02f5a01
Revises: d3a7c81e4f90
Create Date: 2026-08-05 23:40:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = "e4b8d02f5a01"
down_revision = "d3a7c81e4f90"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "disciplina_colaboradores",
        sa.Column("disciplina_id", sa.Integer(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["disciplina_id"], ["disciplinas.id"]),
        sa.ForeignKeyConstraint(["usuario_id"], ["usuarios.id"]),
        sa.PrimaryKeyConstraint("disciplina_id", "usuario_id"),
    )

    with op.batch_alter_table("disciplinas", schema=None) as batch_op:
        batch_op.drop_constraint("uq_disciplina_usuario_semestre_codigo_turma", type_="unique")
        batch_op.create_unique_constraint(
            "uq_disciplina_semestre_codigo_turma",
            ["semestre_id", "codigo", "turma"],
        )

    with op.batch_alter_table("avaliacoes", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("em_grupo", sa.Boolean(), nullable=False, server_default=sa.false())
        )

    op.create_table(
        "grupos",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("disciplina_id", sa.Integer(), nullable=False),
        sa.Column("avaliacao_id", sa.Integer(), nullable=True),
        sa.Column("nome", sa.String(length=80), nullable=False),
        sa.Column("ordem", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["avaliacao_id"], ["avaliacoes.id"]),
        sa.ForeignKeyConstraint(["disciplina_id"], ["disciplinas.id"]),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "grupo_membros",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("grupo_id", sa.Integer(), nullable=False),
        sa.Column("aluno_disciplina_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["aluno_disciplina_id"], ["alunos_disciplina.id"]),
        sa.ForeignKeyConstraint(["grupo_id"], ["grupos.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("grupo_id", "aluno_disciplina_id", name="uq_grupo_aluno"),
    )


def downgrade():
    op.drop_table("grupo_membros")
    op.drop_table("grupos")

    with op.batch_alter_table("avaliacoes", schema=None) as batch_op:
        batch_op.drop_column("em_grupo")

    with op.batch_alter_table("disciplinas", schema=None) as batch_op:
        batch_op.drop_constraint("uq_disciplina_semestre_codigo_turma", type_="unique")
        batch_op.create_unique_constraint(
            "uq_disciplina_usuario_semestre_codigo_turma",
            ["usuario_id", "semestre_id", "codigo", "turma"],
        )

    op.drop_table("disciplina_colaboradores")
