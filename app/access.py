"""Controle de acesso a disciplinas por professor."""
from flask import flash
from flask_login import current_user

from app.extensions import db
from app.models import Disciplina


def pode_acessar_disciplina(disciplina: Disciplina | None) -> bool:
    if disciplina is None:
        return False
    if not current_user.is_authenticated:
        return False
    if current_user.is_admin:
        return True
    return disciplina.usuario_id == current_user.id


def pode_editar_disciplina(disciplina: Disciplina | None) -> bool:
    """Professor só edita as próprias; admin pode editar qualquer uma."""
    return pode_acessar_disciplina(disciplina)


def get_disciplina_acessivel(disciplina_id: int) -> Disciplina | None:
    disciplina = db.session.get(Disciplina, disciplina_id)
    if not pode_acessar_disciplina(disciplina):
        flash("Disciplina não encontrada ou sem permissão de acesso.", "danger")
        return None
    return disciplina


def query_disciplinas_do_usuario(usuario=None):
    usuario = usuario or current_user
    return Disciplina.query.filter_by(usuario_id=usuario.id)


def query_disciplinas_de_outros():
    """Somente para admin: disciplinas que não são do usuário atual."""
    return Disciplina.query.filter(Disciplina.usuario_id != current_user.id)
