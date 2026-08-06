from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required

from app.access import get_disciplina_acessivel
from app.extensions import db
from app.models import AlunoDisciplina, Avaliacao, Grupo, Nota
from app.notas.forms import AvaliacaoForm
from app.services.academico import carregar_notas_map, carregar_notas_objetos, media_ponderada_de_mapas
from app.services.grupos import (
    alunos_sem_grupo,
    copiar_padrao_para_avaliacao,
    garantir_grupos_avaliacao,
    listar_grupos_avaliacao,
    mapa_aluno_grupo,
    nota_representativa_grupo,
    salvar_divisao_grupos,
)

notas_bp = Blueprint("notas", __name__, url_prefix="/disciplinas/<int:disciplina_id>/notas")


def _get_disciplina(disciplina_id):
    return get_disciplina_acessivel(disciplina_id)


def _aplicar_nota(existentes, novos, aluno_id, avaliacao_id, valor):
    chave = (aluno_id, avaliacao_id)
    nota = existentes.get(chave)
    if nota:
        nota.valor = valor
    elif valor is not None:
        novos.append(
            Nota(avaliacao_id=avaliacao_id, aluno_disciplina_id=aluno_id, valor=valor)
        )


@notas_bp.route("/", methods=["GET", "POST"])
@login_required
def lancamento(disciplina_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    avaliacoes = disciplina.avaliacoes.order_by(Avaliacao.ordem).all()
    alunos = disciplina.alunos.order_by(AlunoDisciplina.nome).all()

    # Grupos por avaliação em grupo
    grupos_por_av: dict[int, list] = {}
    aluno_grupo_por_av: dict[int, dict] = {}
    for av in avaliacoes:
        if av.em_grupo:
            grupos = listar_grupos_avaliacao(av.id)
            grupos_por_av[av.id] = grupos
            aluno_grupo_por_av[av.id] = mapa_aluno_grupo(grupos)

    if request.method == "POST":
        existentes = carregar_notas_objetos(disciplina.id)
        novos: list[Nota] = []

        # 1) Notas por grupo → replica aos membros
        for av in avaliacoes:
            if not av.em_grupo:
                continue
            for grupo in grupos_por_av.get(av.id, []):
                field = f"nota_grupo_{grupo.id}_{av.id}"
                raw = request.form.get(field, "").strip().replace(",", ".")
                if field not in request.form:
                    continue
                valor = None
                if raw:
                    try:
                        valor = float(raw)
                        if valor < 0 or valor > 10:
                            flash(f"Nota inválida para {grupo.nome} em {av.nome}.", "danger")
                            return redirect(url_for("notas.lancamento", disciplina_id=disciplina.id))
                    except ValueError:
                        flash(f"Nota inválida para {grupo.nome} em {av.nome}.", "danger")
                        return redirect(url_for("notas.lancamento", disciplina_id=disciplina.id))
                for m in grupo.membros:
                    _aplicar_nota(existentes, novos, m.aluno_disciplina_id, av.id, valor)

        # 2) Notas individuais (avaliações individuais + alunos sem grupo)
        for aluno in alunos:
            for avaliacao in avaliacoes:
                if avaliacao.em_grupo:
                    if aluno.id in aluno_grupo_por_av.get(avaliacao.id, {}):
                        continue  # já tratado pelo grupo
                field = f"nota_{aluno.id}_{avaliacao.id}"
                if field not in request.form:
                    continue
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
                _aplicar_nota(existentes, novos, aluno.id, avaliacao.id, valor)

        if novos:
            db.session.add_all(novos)
        db.session.commit()
        flash("Notas salvas com sucesso.", "success")
        return redirect(url_for("notas.lancamento", disciplina_id=disciplina.id))

    notas_map = carregar_notas_map(disciplina.id)
    linhas = [
        {
            "aluno": aluno,
            "notas": {a.id: notas_map.get((aluno.id, a.id)) for a in avaliacoes},
            "media": media_ponderada_de_mapas(aluno.id, avaliacoes, notas_map),
            "grupos": {
                av.id: aluno_grupo_por_av.get(av.id, {}).get(aluno.id)
                for av in avaliacoes
                if av.em_grupo
            },
        }
        for aluno in alunos
    ]

    blocos_grupo = []
    for av in avaliacoes:
        if not av.em_grupo:
            continue
        grupos = grupos_por_av.get(av.id, [])
        blocos_grupo.append(
            {
                "avaliacao": av,
                "grupos": [
                    {
                        "grupo": g,
                        "nota": nota_representativa_grupo(g, av.id, notas_map),
                        "membros": [m.aluno for m in g.membros],
                    }
                    for g in grupos
                ],
            }
        )

    return render_template(
        "notas/lancamento.html",
        disciplina=disciplina,
        avaliacoes=avaliacoes,
        linhas=linhas,
        blocos_grupo=blocos_grupo,
        aluno_grupo_por_av=aluno_grupo_por_av,
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
            coluna_sigaa=form.coluna_sigaa.data,
            em_grupo=bool(form.em_grupo.data),
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
        avaliacao.coluna_sigaa = form.coluna_sigaa.data
        avaliacao.em_grupo = bool(form.em_grupo.data)
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


@notas_bp.route("/avaliacoes/<int:avaliacao_id>/grupos", methods=["GET", "POST"])
@login_required
def grupos_avaliacao(disciplina_id, avaliacao_id):
    disciplina = _get_disciplina(disciplina_id)
    if disciplina is None:
        return redirect(url_for("disciplinas.listar"))

    avaliacao = db.session.get(Avaliacao, avaliacao_id)
    if avaliacao is None or avaliacao.disciplina_id != disciplina.id:
        flash("Avaliação não encontrada.", "danger")
        return redirect(url_for("notas.avaliacoes", disciplina_id=disciplina.id))

    if not avaliacao.em_grupo:
        flash("Marque a avaliação como em grupo para dividir turmas.", "warning")
        return redirect(
            url_for("notas.editar_avaliacao", disciplina_id=disciplina.id, avaliacao_id=avaliacao.id)
        )

    form_action = url_for(
        "notas.grupos_avaliacao", disciplina_id=disciplina.id, avaliacao_id=avaliacao.id
    )
    alunos = disciplina.alunos.order_by(AlunoDisciplina.nome).all()

    if request.method == "POST":
        acao = request.form.get("acao", "salvar")
        if acao == "recarregar_padrao":
            copiar_padrao_para_avaliacao(disciplina.id, avaliacao)
            flash("Grupos recarregados a partir do padrão da disciplina.", "success")
            return redirect(form_action)
        if acao == "adicionar_grupo":
            grupos = listar_grupos_avaliacao(avaliacao.id)
            n = len(grupos) + 1
            db.session.add(
                Grupo(
                    disciplina_id=disciplina.id,
                    avaliacao_id=avaliacao.id,
                    nome=f"Grupo {n}",
                    ordem=n - 1,
                )
            )
            db.session.commit()
            flash("Grupo adicionado.", "success")
            return redirect(form_action)

        nomes = request.form.getlist("grupo_nome")
        membros_por_indice: list[list[int]] = []
        for i in range(len(nomes)):
            raw_ids = request.form.getlist(f"membros_{i}")
            membros_por_indice.append([int(x) for x in raw_ids if x.isdigit()])
        salvar_divisao_grupos(disciplina.id, avaliacao.id, nomes, membros_por_indice)
        flash("Grupos da avaliação salvos.", "success")
        return redirect(form_action)

    garantir_grupos_avaliacao(disciplina.id, avaliacao)
    grupos = listar_grupos_avaliacao(avaliacao.id)
    sem_grupo = alunos_sem_grupo(disciplina.id, grupos)
    return render_template(
        "disciplinas/grupos.html",
        disciplina=disciplina,
        avaliacao=avaliacao,
        grupos=grupos,
        alunos=alunos,
        sem_grupo=sem_grupo,
        titulo=f"Grupos — {avaliacao.nome}",
        subtitulo="Por padrão, copia os grupos da disciplina; você pode ajustar livremente.",
        form_action=form_action,
        mostrar_recarregar=True,
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
