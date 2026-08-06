"""Serviço de grupos de alunos (padrão da disciplina e por avaliação)."""
from app.extensions import db
from app.models import AlunoDisciplina, Avaliacao, Grupo, GrupoMembro


def listar_grupos_padrao(disciplina_id: int) -> list[Grupo]:
    return (
        Grupo.query.filter_by(disciplina_id=disciplina_id, avaliacao_id=None)
        .order_by(Grupo.ordem, Grupo.nome)
        .all()
    )


def listar_grupos_avaliacao(avaliacao_id: int) -> list[Grupo]:
    return (
        Grupo.query.filter_by(avaliacao_id=avaliacao_id)
        .order_by(Grupo.ordem, Grupo.nome)
        .all()
    )


def alunos_sem_grupo(disciplina_id: int, grupos: list[Grupo]) -> list[AlunoDisciplina]:
    em_grupo = {m.aluno_disciplina_id for g in grupos for m in g.membros}
    return [
        a
        for a in AlunoDisciplina.query.filter_by(disciplina_id=disciplina_id)
        .order_by(AlunoDisciplina.nome)
        .all()
        if a.id not in em_grupo
    ]


def limpar_grupos(grupos: list[Grupo]) -> None:
    for g in grupos:
        db.session.delete(g)


def copiar_padrao_para_avaliacao(disciplina_id: int, avaliacao: Avaliacao) -> list[Grupo]:
    """Substitui grupos da avaliação pelos do padrão da disciplina."""
    existentes = listar_grupos_avaliacao(avaliacao.id)
    limpar_grupos(existentes)
    db.session.flush()

    novos: list[Grupo] = []
    for g in listar_grupos_padrao(disciplina_id):
        novo = Grupo(
            disciplina_id=disciplina_id,
            avaliacao_id=avaliacao.id,
            nome=g.nome,
            ordem=g.ordem,
        )
        db.session.add(novo)
        db.session.flush()
        for m in g.membros:
            db.session.add(
                GrupoMembro(grupo_id=novo.id, aluno_disciplina_id=m.aluno_disciplina_id)
            )
        novos.append(novo)
    db.session.commit()
    return novos


def garantir_grupos_avaliacao(disciplina_id: int, avaliacao: Avaliacao) -> list[Grupo]:
    """Na primeira abertura, copia o padrão se a avaliação ainda não tem grupos."""
    grupos = listar_grupos_avaliacao(avaliacao.id)
    if grupos:
        return grupos
    padrao = listar_grupos_padrao(disciplina_id)
    if not padrao:
        return []
    return copiar_padrao_para_avaliacao(disciplina_id, avaliacao)


def salvar_divisao_grupos(
    disciplina_id: int,
    avaliacao_id: int | None,
    nomes: list[str],
    membros_por_indice: list[list[int]],
) -> None:
    """
    Recria grupos do escopo a partir de nomes e listas de aluno_disciplina_id.
    membros_por_indice[i] corresponde a nomes[i].
    """
    if avaliacao_id is None:
        existentes = listar_grupos_padrao(disciplina_id)
    else:
        existentes = listar_grupos_avaliacao(avaliacao_id)
    limpar_grupos(existentes)
    db.session.flush()

    vistos: set[int] = set()
    for ordem, nome in enumerate(nomes):
        nome = (nome or "").strip()
        if not nome:
            continue
        grupo = Grupo(
            disciplina_id=disciplina_id,
            avaliacao_id=avaliacao_id,
            nome=nome,
            ordem=ordem,
        )
        db.session.add(grupo)
        db.session.flush()
        for aluno_id in membros_por_indice[ordem] if ordem < len(membros_por_indice) else []:
            if aluno_id in vistos:
                continue
            aluno = db.session.get(AlunoDisciplina, aluno_id)
            if aluno is None or aluno.disciplina_id != disciplina_id:
                continue
            vistos.add(aluno_id)
            db.session.add(GrupoMembro(grupo_id=grupo.id, aluno_disciplina_id=aluno_id))

    db.session.commit()


def mapa_aluno_grupo(grupos: list[Grupo]) -> dict[int, Grupo]:
    """aluno_disciplina_id -> Grupo."""
    out: dict[int, Grupo] = {}
    for g in grupos:
        for m in g.membros:
            out[m.aluno_disciplina_id] = g
    return out


def nota_representativa_grupo(grupo: Grupo, avaliacao_id: int, notas_map: dict) -> float | None:
    """Usa a primeira nota não-nula dos membros (devem ser iguais após lançamento em grupo)."""
    for m in grupo.membros:
        valor = notas_map.get((m.aluno_disciplina_id, avaliacao_id))
        if valor is not None:
            return valor
    return None
