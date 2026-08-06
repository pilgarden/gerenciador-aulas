from flask import Blueprint, render_template
from flask_login import current_user, login_required

from app.access import query_disciplinas_de_outros
from app.models import AlunoDisciplina, Disciplina, Semestre, Usuario

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def index():
    disciplina_ids = [
        row[0]
        for row in Disciplina.query.filter_by(usuario_id=current_user.id)
        .with_entities(Disciplina.id)
        .all()
    ]
    stats = {
        "semestres": Semestre.query.count(),
        "disciplinas": len(disciplina_ids),
        "alunos": (
            AlunoDisciplina.query.filter(AlunoDisciplina.disciplina_id.in_(disciplina_ids)).count()
            if disciplina_ids
            else 0
        ),
        "usuarios": Usuario.query.filter_by(ativo=True).count(),
    }

    semestre_ativo = Semestre.query.filter_by(ativo=True).first()
    disciplinas = []
    if semestre_ativo:
        disciplinas = (
            Disciplina.query.filter_by(usuario_id=current_user.id, semestre_id=semestre_ativo.id)
            .order_by(Disciplina.codigo)
            .limit(10)
            .all()
        )

    outras_count = 0
    if current_user.is_admin:
        outras_count = query_disciplinas_de_outros().count()

    return render_template(
        "main/index.html",
        stats=stats,
        semestre_ativo=semestre_ativo,
        disciplinas=disciplinas,
        outras_count=outras_count,
    )
