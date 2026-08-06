from flask import Blueprint, flash, redirect, render_template, send_file, url_for
from flask_login import current_user, login_required
from io import BytesIO

from app.access import get_disciplina_acessivel
from app.models import Avaliacao
from app.relatorios.forms import RelatorioPdfForm
from app.services.relatorio_pdf import RelatorioConfig, gerar_pdf_relatorio, nome_arquivo_relatorio

relatorios_bp = Blueprint(
    "relatorios", __name__, url_prefix="/disciplinas/<int:disciplina_id>/relatorios"
)


@relatorios_bp.route("/", methods=["GET", "POST"])
@login_required
def gerar(disciplina_id):
    disciplina = get_disciplina_acessivel(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    form = RelatorioPdfForm()
    avaliacoes = disciplina.avaliacoes.order_by(Avaliacao.ordem).all()
    form.avaliacoes.choices = [(a.id, a.nome) for a in avaliacoes]

    cab_choices = [("simples", "Cabeçalho simples / personalizado")]
    if current_user.acesso_cabecalho_unir or current_user.is_admin:
        cab_choices.insert(0, ("unir", "Pré-formatado UNIR — Engenharia Civil"))
    form.cabecalho.choices = cab_choices

    if form.validate_on_submit():
        usar_unir = form.cabecalho.data == "unir" and (
            current_user.acesso_cabecalho_unir or current_user.is_admin
        )
        if form.cabecalho.data == "unir" and not usar_unir:
            flash("Você não tem permissão para o cabeçalho UNIR.", "danger")
            return redirect(url_for("relatorios.gerar", disciplina_id=disciplina.id))

        config = RelatorioConfig(
            tipo=form.tipo.data,
            matricula_modo=form.matricula_modo.data,
            digitos_matricula=form.digitos_matricula.data or 4,
            incluir_nome=bool(form.incluir_nome.data),
            incluir_media=bool(form.incluir_media.data),
            avaliacao_ids=list(form.avaliacoes.data or []),
            usar_cabecalho_unir=usar_unir,
            titulo_custom=form.titulo_custom.data or "",
            linha1=form.linha1.data or "",
            linha2=form.linha2.data or "",
            linha3=form.linha3.data or "",
        )
        # Admin sem flag ainda pode usar cabeçalho UNIR na geração (já tratado acima)
        professor = current_user
        if usar_unir and not professor.acesso_cabecalho_unir and professor.is_admin:
            # permite preview admin: força flag temporária só na checagem do serviço
            class _Proxy:
                def __init__(self, u):
                    self._u = u

                def __getattr__(self, name):
                    if name == "acesso_cabecalho_unir":
                        return True
                    return getattr(self._u, name)

            professor = _Proxy(current_user)

        pdf = gerar_pdf_relatorio(disciplina, professor, config)
        return send_file(
            BytesIO(pdf),
            as_attachment=True,
            download_name=nome_arquivo_relatorio(disciplina, config.tipo),
            mimetype="application/pdf",
        )

    if not form.is_submitted():
        form.linha1.data = "UNIVERSIDADE FEDERAL DE RONDÔNIA (UNIR)" if current_user.acesso_cabecalho_unir else ""
        form.incluir_nome.data = True
        form.incluir_media.data = True
        if current_user.acesso_cabecalho_unir or current_user.is_admin:
            form.cabecalho.data = "unir"

    return render_template(
        "relatorios/gerar.html",
        disciplina=disciplina,
        form=form,
        pode_unir=current_user.acesso_cabecalho_unir or current_user.is_admin,
    )
