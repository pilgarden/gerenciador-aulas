import json

from flask import Blueprint, flash, redirect, render_template, request, send_file, session, url_for
from io import BytesIO
from flask_login import current_user, login_required

from app import admin_required
from app.access import get_disciplina_acessivel, query_disciplinas_de_outros, query_disciplinas_do_usuario
from app.extensions import db
from app.models import AlunoDisciplina, Disciplina, Semestre, Usuario
from app.disciplinas.forms import DisciplinaForm, ImportSigaaForm
from app.services.importacao import aplicar_importacao_sigaa
from app.services.sigaa_export import gerar_planilha_sigaa, nome_arquivo_exportacao
from app.services.sigaa_import import (
    SigaaImportError,
    import_result_from_dict,
    import_result_to_dict,
    parse_sigaa_xls,
)

disciplinas_bp = Blueprint("disciplinas", __name__, url_prefix="/disciplinas")

IMPORT_SESSION_KEY = "sigaa_import_preview"


@disciplinas_bp.route("/")
@login_required
def listar():
    semestre_id = request.args.get("semestre_id", type=int)
    query = query_disciplinas_do_usuario().join(Semestre).order_by(
        Semestre.codigo.desc(), Disciplina.codigo
    )
    if semestre_id:
        query = query.filter(Disciplina.semestre_id == semestre_id)
    disciplinas = query.all()
    semestres = Semestre.query.order_by(Semestre.codigo.desc()).all()
    outras_count = 0
    if current_user.is_admin:
        outras_count = query_disciplinas_de_outros().count()
    return render_template(
        "disciplinas/list.html",
        disciplinas=disciplinas,
        semestres=semestres,
        semestre_id=semestre_id,
        outras_count=outras_count,
    )


@disciplinas_bp.route("/outras")
@login_required
@admin_required
def listar_outras():
    """Admin: turmas de outros professores, separadas das próprias."""
    semestre_id = request.args.get("semestre_id", type=int)
    query = (
        query_disciplinas_de_outros()
        .join(Semestre)
        .join(Usuario)
        .order_by(Usuario.nome, Semestre.codigo.desc(), Disciplina.codigo)
    )
    if semestre_id:
        query = query.filter(Disciplina.semestre_id == semestre_id)
    disciplinas = query.all()
    semestres = Semestre.query.order_by(Semestre.codigo.desc()).all()
    return render_template(
        "disciplinas/list_outras.html",
        disciplinas=disciplinas,
        semestres=semestres,
        semestre_id=semestre_id,
    )


@disciplinas_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    if Semestre.query.count() == 0:
        flash("Cadastre um semestre antes de criar disciplinas.", "warning")
        return redirect(url_for("semestres.novo"))

    form = DisciplinaForm()
    form.usuario_id = current_user.id
    semestre_ativo = Semestre.query.filter_by(ativo=True).first()
    if request.method == "GET" and semestre_ativo and form.semestre_id.choices:
        form.semestre_id.data = semestre_ativo.id

    if form.validate_on_submit():
        disciplina = Disciplina(
            usuario_id=current_user.id,
            semestre_id=form.semestre_id.data,
            codigo=form.codigo.data.strip(),
            nome=form.nome.data.strip(),
            turma=form.turma.data.strip(),
            carga_horaria=form.carga_horaria.data,
            aulas_previstas=form.aulas_previstas.data,
        )
        db.session.add(disciplina)
        db.session.commit()
        flash("Disciplina criada com sucesso.", "success")
        return redirect(url_for("disciplinas.listar"))

    return render_template("disciplinas/form.html", form=form, titulo="Nova disciplina")


@disciplinas_bp.route("/<int:disciplina_id>")
@login_required
def detalhe(disciplina_id):
    disciplina = get_disciplina_acessivel(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    alunos = disciplina.alunos.order_by(AlunoDisciplina.nome).limit(5).all()
    total_alunos = disciplina.alunos.count()
    eh_propria = disciplina.usuario_id == current_user.id

    return render_template(
        "disciplinas/detalhe.html",
        disciplina=disciplina,
        alunos=alunos,
        total_alunos=total_alunos,
        eh_propria=eh_propria,
    )


@disciplinas_bp.route("/<int:disciplina_id>/editar", methods=["GET", "POST"])
@login_required
def editar(disciplina_id):
    disciplina = get_disciplina_acessivel(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    form = DisciplinaForm(obj=disciplina)
    form.disciplina_id = disciplina.id
    form.usuario_id = disciplina.usuario_id

    if form.validate_on_submit():
        disciplina.semestre_id = form.semestre_id.data
        disciplina.codigo = form.codigo.data.strip()
        disciplina.nome = form.nome.data.strip()
        disciplina.turma = form.turma.data.strip()
        disciplina.carga_horaria = form.carga_horaria.data
        disciplina.aulas_previstas = form.aulas_previstas.data
        db.session.commit()
        flash("Disciplina atualizada.", "success")
        return redirect(url_for("disciplinas.detalhe", disciplina_id=disciplina.id))

    return render_template(
        "disciplinas/form.html",
        form=form,
        titulo=f"Editar {disciplina.codigo}",
        disciplina=disciplina,
    )


@disciplinas_bp.route("/<int:disciplina_id>/excluir", methods=["POST"])
@login_required
def excluir(disciplina_id):
    disciplina = get_disciplina_acessivel(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    db.session.delete(disciplina)
    db.session.commit()
    flash("Disciplina excluída.", "success")
    return redirect(url_for("disciplinas.listar"))


@disciplinas_bp.route("/importar", methods=["GET", "POST"])
@login_required
def importar():
    form = ImportSigaaForm()
    if form.validate_on_submit():
        arquivo = form.arquivo.data
        try:
            result = parse_sigaa_xls(arquivo.read())
        except SigaaImportError as exc:
            flash(str(exc), "danger")
            return render_template("disciplinas/importar.html", form=form)

        session[IMPORT_SESSION_KEY] = json.dumps(import_result_to_dict(result))
        return redirect(url_for("disciplinas.importar_preview"))

    return render_template("disciplinas/importar.html", form=form)


@disciplinas_bp.route("/importar/preview")
@login_required
def importar_preview():
    raw = session.get(IMPORT_SESSION_KEY)
    if not raw:
        flash("Nenhuma planilha em análise. Faça o upload novamente.", "warning")
        return redirect(url_for("disciplinas.importar"))

    preview = import_result_from_dict(json.loads(raw))
    return render_template("disciplinas/importar_preview.html", preview=preview)


@disciplinas_bp.route("/importar/confirmar", methods=["POST"])
@login_required
def importar_confirmar():
    raw = session.get(IMPORT_SESSION_KEY)
    if not raw:
        flash("Nenhuma planilha em análise. Faça o upload novamente.", "warning")
        return redirect(url_for("disciplinas.importar"))

    preview = import_result_from_dict(json.loads(raw))
    disciplina, stats = aplicar_importacao_sigaa(preview, usuario_id=current_user.id)
    session.pop(IMPORT_SESSION_KEY, None)

    flash(
        f"Importação concluída: {stats['criados']} aluno(s) criado(s), "
        f"{stats['atualizados']} atualizado(s).",
        "success",
    )
    return redirect(url_for("disciplinas.detalhe", disciplina_id=disciplina.id))


@disciplinas_bp.route("/<int:disciplina_id>/exportar")
@login_required
def exportar(disciplina_id):
    disciplina = get_disciplina_acessivel(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    if disciplina.alunos.count() == 0:
        flash("Cadastre alunos antes de exportar.", "warning")
        return redirect(url_for("disciplinas.detalhe", disciplina_id=disciplina.id))

    conteudo = gerar_planilha_sigaa(disciplina)
    return send_file(
        BytesIO(conteudo),
        as_attachment=True,
        download_name=nome_arquivo_exportacao(disciplina),
        mimetype="application/vnd.ms-excel",
    )
