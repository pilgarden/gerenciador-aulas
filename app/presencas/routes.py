from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.access import get_disciplina_acessivel
from app.extensions import db
from app.models import AlunoDisciplina, Aula, Presenca
from app.presencas.forms import AulaForm

presencas_bp = Blueprint("presencas", __name__, url_prefix="/disciplinas/<int:disciplina_id>/aulas")


def _get_disciplina(disciplina_id):
    return get_disciplina_acessivel(disciplina_id)


@presencas_bp.route("/")
@login_required
def listar(disciplina_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    aulas = disciplina.aulas.order_by(Aula.data.desc()).all()
    return render_template("presencas/list.html", disciplina=disciplina, aulas=aulas)


@presencas_bp.route("/nova", methods=["GET", "POST"])
@login_required
def nova(disciplina_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    form = AulaForm()
    form.disciplina_id = disciplina.id

    if form.validate_on_submit():
        ultima = disciplina.aulas.order_by(Aula.numero.desc()).first()
        numero = form.numero.data or ((ultima.numero or 0) + 1 if ultima else 1)

        aula = Aula(
            disciplina_id=disciplina.id,
            data=form.data.data,
            numero=numero,
            conteudo=form.conteudo.data.strip() if form.conteudo.data else None,
        )
        db.session.add(aula)
        db.session.commit()
        flash("Aula criada. Registre a chamada.", "success")
        return redirect(url_for("presencas.chamada", disciplina_id=disciplina.id, aula_id=aula.id))

    return render_template(
        "presencas/form_aula.html",
        form=form,
        disciplina=disciplina,
        titulo="Nova aula",
    )


@presencas_bp.route("/<int:aula_id>/editar", methods=["GET", "POST"])
@login_required
def editar(disciplina_id, aula_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    aula = db.session.get(Aula, aula_id)
    if aula is None or aula.disciplina_id != disciplina.id:
        flash("Aula não encontrada.", "danger")
        return redirect(url_for("presencas.listar", disciplina_id=disciplina.id))

    form = AulaForm(obj=aula)
    form.disciplina_id = disciplina.id
    form.aula_id = aula.id

    if form.validate_on_submit():
        aula.data = form.data.data
        aula.numero = form.numero.data
        aula.conteudo = form.conteudo.data.strip() if form.conteudo.data else None
        db.session.commit()
        flash("Aula atualizada.", "success")
        return redirect(url_for("presencas.listar", disciplina_id=disciplina.id))

    return render_template(
        "presencas/form_aula.html",
        form=form,
        disciplina=disciplina,
        aula=aula,
        titulo=f"Editar aula {aula.data.strftime('%d/%m/%Y')}",
    )


@presencas_bp.route("/<int:aula_id>/excluir", methods=["POST"])
@login_required
def excluir(disciplina_id, aula_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    aula = db.session.get(Aula, aula_id)
    if aula is None or aula.disciplina_id != disciplina.id:
        flash("Aula não encontrada.", "danger")
        return redirect(url_for("presencas.listar", disciplina_id=disciplina.id))

    db.session.delete(aula)
    db.session.commit()
    flash("Aula excluída.", "success")
    return redirect(url_for("presencas.listar", disciplina_id=disciplina.id))


@presencas_bp.route("/<int:aula_id>/chamada", methods=["GET", "POST"])
@login_required
def chamada(disciplina_id, aula_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    aula = db.session.get(Aula, aula_id)
    if aula is None or aula.disciplina_id != disciplina.id:
        flash("Aula não encontrada.", "danger")
        return redirect(url_for("presencas.listar", disciplina_id=disciplina.id))

    alunos = disciplina.alunos.order_by(AlunoDisciplina.nome).all()
    if not alunos:
        flash("Cadastre alunos antes de fazer a chamada.", "warning")
        return redirect(url_for("alunos.listar", disciplina_id=disciplina.id))

    if request.method == "POST":
        existentes = {
            p.aluno_disciplina_id: p
            for p in Presenca.query.filter_by(aula_id=aula.id).all()
        }
        novas: list[Presenca] = []

        for aluno in alunos:
            status = request.form.get(f"presenca_{aluno.id}", Presenca.STATUS_PRESENTE)
            if status not in (
                Presenca.STATUS_PRESENTE,
                Presenca.STATUS_AUSENTE,
                Presenca.STATUS_JUSTIFICADO,
            ):
                status = Presenca.STATUS_PRESENTE

            presenca = existentes.get(aluno.id)
            if presenca:
                presenca.status = status
            else:
                novas.append(
                    Presenca(
                        aula_id=aula.id,
                        aluno_disciplina_id=aluno.id,
                        status=status,
                        origem=Presenca.STATUS_MANUAL,
                    )
                )

        if novas:
            db.session.add_all(novas)
        db.session.commit()
        flash("Chamada registrada com sucesso.", "success")
        return redirect(url_for("presencas.listar", disciplina_id=disciplina.id))

    presencas = {p.aluno_disciplina_id: p.status for p in aula.presencas.all()}
    return render_template(
        "presencas/chamada.html",
        disciplina=disciplina,
        aula=aula,
        alunos=alunos,
        presencas=presencas,
        status_opcoes=[
            (Presenca.STATUS_PRESENTE, "Presente", "success"),
            (Presenca.STATUS_AUSENTE, "Ausente", "danger"),
            (Presenca.STATUS_JUSTIFICADO, "Justificado", "warning"),
        ],
    )


@presencas_bp.route("/resumo")
@login_required
def resumo(disciplina_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    alunos = disciplina.alunos.order_by(AlunoDisciplina.nome).all()
    aluno_ids = [a.id for a in alunos]
    total_aulas = disciplina.aulas.count()

    # Uma query com todas as presenças da disciplina
    contagens = {
        aid: {"P": 0, "A": 0, "J": 0}
        for aid in aluno_ids
    }
    if aluno_ids:
        presencas = (
            Presenca.query.join(Aula)
            .filter(Aula.disciplina_id == disciplina.id)
            .filter(Presenca.aluno_disciplina_id.in_(aluno_ids))
            .all()
        )
        for p in presencas:
            if p.aluno_disciplina_id in contagens and p.status in contagens[p.aluno_disciplina_id]:
                contagens[p.aluno_disciplina_id][p.status] += 1

    resumo_alunos = [
        {
            "aluno": aluno,
            "faltas": contagens[aluno.id]["A"],
            "justificadas": contagens[aluno.id]["J"],
            "presencas": contagens[aluno.id]["P"],
        }
        for aluno in alunos
    ]

    return render_template(
        "presencas/resumo.html",
        disciplina=disciplina,
        resumo_alunos=resumo_alunos,
        total_aulas=total_aulas,
    )
