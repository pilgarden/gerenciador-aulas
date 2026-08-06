"""Controle de acesso a disciplinas por professor (dono + colaboradores)."""
from flask import flash
from flask_login import current_user
from sqlalchemy import or_

from app.extensions import db
from app.models import Disciplina, Usuario, disciplina_colaboradores


def pode_acessar_disciplina(disciplina: Disciplina | None) -> bool:
    if disciplina is None:
        return False
    if not current_user.is_authenticated:
        return False
    return disciplina.tem_acesso(current_user)


def pode_editar_disciplina(disciplina: Disciplina | None) -> bool:
    return pode_acessar_disciplina(disciplina)


def get_disciplina_acessivel(disciplina_id: int) -> Disciplina | None:
    disciplina = db.session.get(Disciplina, disciplina_id)
    if not pode_acessar_disciplina(disciplina):
        flash("Disciplina não encontrada ou sem permissão de acesso.", "danger")
        return None
    return disciplina


def query_disciplinas_do_usuario(usuario=None):
    """Disciplinas em que o usuário é dono ou colaborador."""
    usuario = usuario or current_user
    collab_ids = (
        db.session.query(disciplina_colaboradores.c.disciplina_id)
        .filter(disciplina_colaboradores.c.usuario_id == usuario.id)
        .scalar_subquery()
    )
    return Disciplina.query.filter(
        or_(Disciplina.usuario_id == usuario.id, Disciplina.id.in_(collab_ids))
    )


def query_disciplinas_de_outros():
    """Admin: disciplinas em que o usuário atual não é dono nem colaborador."""
    collab_ids = (
        db.session.query(disciplina_colaboradores.c.disciplina_id)
        .filter(disciplina_colaboradores.c.usuario_id == current_user.id)
        .scalar_subquery()
    )
    return Disciplina.query.filter(
        Disciplina.usuario_id != current_user.id,
        ~Disciplina.id.in_(collab_ids),
    )


def usuario_tem_acesso_disciplina(disciplina: Disciplina, usuario: Usuario) -> bool:
    return disciplina.tem_acesso(usuario)
