from flask import Blueprint, render_template
from flask_login import login_required

from app.models import Disciplina, Semestre, Usuario, AlunoDisciplina

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
@login_required
def index():
    stats = {
        "semestres": Semestre.query.count(),
        "disciplinas": Disciplina.query.count(),
        "alunos": AlunoDisciplina.query.count(),
        "usuarios": Usuario.query.filter_by(ativo=True).count(),
    }
    semestre_ativo = Semestre.query.filter_by(ativo=True).first()
    disciplinas = []
    if semestre_ativo:
        disciplinas = (
            Disciplina.query.filter_by(semestre_id=semestre_ativo.id)
            .order_by(Disciplina.codigo)
            .limit(10)
            .all()
        )

    return render_template(
        "main/index.html",
        stats=stats,
        semestre_ativo=semestre_ativo,
        disciplinas=disciplinas,
    )
