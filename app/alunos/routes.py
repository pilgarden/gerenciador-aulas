import json

from flask import Blueprint, flash, redirect, render_template, session, url_for
from flask_login import login_required

from app.access import get_disciplina_acessivel
from app.extensions import db
from app.models import AlunoDisciplina
from app.alunos.forms import AlunoForm
from app.disciplinas.forms import ImportSigaaForm
from app.services.importacao import aplicar_importacao_sigaa
from app.services.sigaa_import import (
    SigaaImportError,
    import_result_from_dict,
    import_result_to_dict,
    parse_sigaa_xls,
)

alunos_bp = Blueprint("alunos", __name__, url_prefix="/disciplinas/<int:disciplina_id>/alunos")

IMPORT_SESSION_KEY = "sigaa_import_preview_disciplina"


def _get_disciplina(disciplina_id):
    return get_disciplina_acessivel(disciplina_id)


@alunos_bp.route("/")
@login_required
def listar(disciplina_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    alunos = disciplina.alunos.order_by(AlunoDisciplina.nome).all()
    return render_template("alunos/list.html", disciplina=disciplina, alunos=alunos)


@alunos_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo(disciplina_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    form = AlunoForm()
    form.disciplina_id = disciplina.id

    if form.validate_on_submit():
        aluno = AlunoDisciplina(
            disciplina_id=disciplina.id,
            matricula=form.matricula.data.strip(),
            nome=form.nome.data.strip(),
            faltas_sigaa=form.faltas_sigaa.data or 0,
            situacao=form.situacao.data.strip() if form.situacao.data else None,
        )
        db.session.add(aluno)
        db.session.commit()
        flash("Aluno cadastrado com sucesso.", "success")
        return redirect(url_for("alunos.listar", disciplina_id=disciplina.id))

    return render_template(
        "alunos/form.html",
        form=form,
        disciplina=disciplina,
        titulo="Novo aluno",
    )


@alunos_bp.route("/<int:aluno_id>/editar", methods=["GET", "POST"])
@login_required
def editar(disciplina_id, aluno_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    aluno = db.session.get(AlunoDisciplina, aluno_id)
    if aluno is None or aluno.disciplina_id != disciplina.id:
        flash("Aluno não encontrado.", "danger")
        return redirect(url_for("alunos.listar", disciplina_id=disciplina.id))

    form = AlunoForm(obj=aluno)
    form.disciplina_id = disciplina.id
    form.aluno_id = aluno.id

    if form.validate_on_submit():
        aluno.matricula = form.matricula.data.strip()
        aluno.nome = form.nome.data.strip()
        aluno.faltas_sigaa = form.faltas_sigaa.data or 0
        aluno.situacao = form.situacao.data.strip() if form.situacao.data else None
        db.session.commit()
        flash("Aluno atualizado.", "success")
        return redirect(url_for("alunos.listar", disciplina_id=disciplina.id))

    return render_template(
        "alunos/form.html",
        form=form,
        disciplina=disciplina,
        titulo=f"Editar {aluno.nome}",
        aluno=aluno,
    )


@alunos_bp.route("/<int:aluno_id>/excluir", methods=["POST"])
@login_required
def excluir(disciplina_id, aluno_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    aluno = db.session.get(AlunoDisciplina, aluno_id)
    if aluno is None or aluno.disciplina_id != disciplina.id:
        flash("Aluno não encontrado.", "danger")
        return redirect(url_for("alunos.listar", disciplina_id=disciplina.id))

    db.session.delete(aluno)
    db.session.commit()
    flash("Aluno excluído.", "success")
    return redirect(url_for("alunos.listar", disciplina_id=disciplina.id))


@alunos_bp.route("/importar", methods=["GET", "POST"])
@login_required
def importar(disciplina_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    form = ImportSigaaForm()
    if form.validate_on_submit():
        try:
            result = parse_sigaa_xls(form.arquivo.data.read())
        except SigaaImportError as exc:
            flash(str(exc), "danger")
            return render_template("alunos/importar.html", form=form, disciplina=disciplina)

        session[f"{IMPORT_SESSION_KEY}_{disciplina.id}"] = json.dumps(import_result_to_dict(result))
        return redirect(url_for("alunos.importar_preview", disciplina_id=disciplina.id))

    return render_template("alunos/importar.html", form=form, disciplina=disciplina)


@alunos_bp.route("/importar/preview")
@login_required
def importar_preview(disciplina_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    raw = session.get(f"{IMPORT_SESSION_KEY}_{disciplina.id}")
    if not raw:
        flash("Nenhuma planilha em análise. Faça o upload novamente.", "warning")
        return redirect(url_for("alunos.importar", disciplina_id=disciplina.id))

    preview = import_result_from_dict(json.loads(raw))
    return render_template(
        "alunos/importar_preview.html",
        preview=preview,
        disciplina=disciplina,
    )


@alunos_bp.route("/importar/confirmar", methods=["POST"])
@login_required
def importar_confirmar(disciplina_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    raw = session.get(f"{IMPORT_SESSION_KEY}_{disciplina.id}")
    if not raw:
        flash("Nenhuma planilha em análise. Faça o upload novamente.", "warning")
        return redirect(url_for("alunos.importar", disciplina_id=disciplina.id))

    preview = import_result_from_dict(json.loads(raw))
    _, stats = aplicar_importacao_sigaa(preview, disciplina_id=disciplina.id)
    session.pop(f"{IMPORT_SESSION_KEY}_{disciplina.id}", None)

    flash(
        f"Importação concluída: {stats['criados']} aluno(s) criado(s), "
        f"{stats['atualizados']} atualizado(s).",
        "success",
    )
    return redirect(url_for("alunos.listar", disciplina_id=disciplina.id))
