from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Disciplina
from app.services.estatisticas import LIMITE_FREQUENCIA, calcular_estatisticas

estatisticas_bp = Blueprint(
    "estatisticas", __name__, url_prefix="/disciplinas/<int:disciplina_id>/estatisticas"
)


@estatisticas_bp.route("/")
@login_required
def index(disciplina_id):
    disciplina = db.session.get(Disciplina, disciplina_id)
    if disciplina is None:
        flash("Disciplina não encontrada.", "danger")
        return redirect(url_for("disciplinas.listar"))

    stats = calcular_estatisticas(disciplina)
    return render_template(
        "estatisticas/index.html",
        disciplina=disciplina,
        stats=stats,
        limite_frequencia=LIMITE_FREQUENCIA,
    )
