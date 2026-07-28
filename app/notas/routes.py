from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.extensions import db
from app.models import AlunoDisciplina, Avaliacao, Disciplina, Nota
from app.notas.forms import AvaliacaoForm
from app.services.academico import calcular_media_aluno

notas_bp = Blueprint("notas", __name__, url_prefix="/disciplinas/<int:disciplina_id>/notas")


def _get_disciplina(disciplina_id):
    disciplina = db.session.get(Disciplina, disciplina_id)
    if disciplina is None:
        flash("Disciplina não encontrada.", "danger")
        return None
    return disciplina


@notas_bp.route("/", methods=["GET", "POST"])
@login_required
def lancamento(disciplina_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    avaliacoes = disciplina.avaliacoes.order_by(Avaliacao.ordem).all()
    alunos = disciplina.alunos.order_by(AlunoDisciplina.nome).all()

    if request.method == "POST":
        for aluno in alunos:
            for avaliacao in avaliacoes:
                field = f"nota_{aluno.id}_{avaliacao.id}"
                raw = request.form.get(field, "").strip().replace(",", ".")
                valor = None
                if raw:
                    try:
                        valor = float(raw)
                        if valor < 0 or valor > 10:
                            flash(f"Nota inválida para {aluno.nome} em {avaliacao.nome}.", "danger")
                            return redirect(url_for("notas.lancamento", disciplina_id=disciplina.id))
                    except ValueError:
                        flash(f"Nota inválida para {aluno.nome} em {avaliacao.nome}.", "danger")
                        return redirect(url_for("notas.lancamento", disciplina_id=disciplina.id))

                nota = Nota.query.filter_by(
                    avaliacao_id=avaliacao.id,
                    aluno_disciplina_id=aluno.id,
                ).first()
                if nota:
                    nota.valor = valor
                elif valor is not None:
                    nota = Nota(
                        avaliacao_id=avaliacao.id,
                        aluno_disciplina_id=aluno.id,
                        valor=valor,
                    )
                    db.session.add(nota)

        db.session.commit()
        flash("Notas salvas com sucesso.", "success")
        return redirect(url_for("notas.lancamento", disciplina_id=disciplina.id))

    notas_map = {}
    for nota in Nota.query.join(Avaliacao).filter(Avaliacao.disciplina_id == disciplina.id).all():
        notas_map[(nota.aluno_disciplina_id, nota.avaliacao_id)] = nota.valor

    linhas = []
    for aluno in alunos:
        linhas.append(
            {
                "aluno": aluno,
                "notas": {a.id: notas_map.get((aluno.id, a.id)) for a in avaliacoes},
                "media": calcular_media_aluno(aluno, disciplina.id),
            }
        )

    return render_template(
        "notas/lancamento.html",
        disciplina=disciplina,
        avaliacoes=avaliacoes,
        linhas=linhas,
    )


@notas_bp.route("/avaliacoes")
@login_required
def avaliacoes(disciplina_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    items = disciplina.avaliacoes.order_by(Avaliacao.ordem).all()
    return render_template("notas/avaliacoes.html", disciplina=disciplina, avaliacoes=items)


@notas_bp.route("/avaliacoes/nova", methods=["GET", "POST"])
@login_required
def nova_avaliacao(disciplina_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    form = AvaliacaoForm()
    form.disciplina_id = disciplina.id

    if form.validate_on_submit():
        ultima = disciplina.avaliacoes.order_by(Avaliacao.ordem.desc()).first()
        ordem = form.ordem.data if form.ordem.data is not None else ((ultima.ordem + 1) if ultima else 0)

        avaliacao = Avaliacao(
            disciplina_id=disciplina.id,
            nome=form.nome.data.strip(),
            peso=form.peso.data or 1.0,
            ordem=ordem,
        )
        db.session.add(avaliacao)
        db.session.commit()
        flash("Avaliação criada.", "success")
        return redirect(url_for("notas.avaliacoes", disciplina_id=disciplina.id))

    return render_template(
        "notas/form_avaliacao.html",
        form=form,
        disciplina=disciplina,
        titulo="Nova avaliação",
    )


@notas_bp.route("/avaliacoes/<int:avaliacao_id>/editar", methods=["GET", "POST"])
@login_required
def editar_avaliacao(disciplina_id, avaliacao_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    avaliacao = db.session.get(Avaliacao, avaliacao_id)
    if avaliacao is None or avaliacao.disciplina_id != disciplina.id:
        flash("Avaliação não encontrada.", "danger")
        return redirect(url_for("notas.avaliacoes", disciplina_id=disciplina.id))

    form = AvaliacaoForm(obj=avaliacao)
    form.disciplina_id = disciplina.id
    form.avaliacao_id = avaliacao.id

    if form.validate_on_submit():
        avaliacao.nome = form.nome.data.strip()
        avaliacao.peso = form.peso.data or 1.0
        avaliacao.ordem = form.ordem.data or 0
        db.session.commit()
        flash("Avaliação atualizada.", "success")
        return redirect(url_for("notas.avaliacoes", disciplina_id=disciplina.id))

    return render_template(
        "notas/form_avaliacao.html",
        form=form,
        disciplina=disciplina,
        avaliacao=avaliacao,
        titulo=f"Editar {avaliacao.nome}",
    )


@notas_bp.route("/avaliacoes/<int:avaliacao_id>/excluir", methods=["POST"])
@login_required
def excluir_avaliacao(disciplina_id, avaliacao_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    avaliacao = db.session.get(Avaliacao, avaliacao_id)
    if avaliacao is None or avaliacao.disciplina_id != disciplina.id:
        flash("Avaliação não encontrada.", "danger")
        return redirect(url_for("notas.avaliacoes", disciplina_id=disciplina.id))

    db.session.delete(avaliacao)
    db.session.commit()
    flash("Avaliação excluída.", "success")
    return redirect(url_for("notas.avaliacoes", disciplina_id=disciplina.id))
