"""Utilitários para presenças e notas (otimizados para poucas queries)."""
from app.models import AlunoDisciplina, Avaliacao, Nota, Presenca


def contar_faltas_aluno(aluno: AlunoDisciplina) -> int:
    return aluno.presencas.filter_by(status=Presenca.STATUS_AUSENTE).count()


def media_ponderada_de_mapas(
    aluno_id: int,
    avaliacoes: list[Avaliacao],
    notas_map: dict[tuple[int, int], float | None],
    excluir_rec: bool = True,
) -> float | None:
    """Calcula média a partir de mapas já carregados (sem novas queries)."""
    total_peso = 0.0
    total_pontos = 0.0
    tem_nota = False

    for avaliacao in avaliacoes:
        if excluir_rec and avaliacao.coluna_sigaa == Avaliacao.COLUNA_REC:
            continue
        valor = notas_map.get((aluno_id, avaliacao.id))
        if valor is None:
            continue
        tem_nota = True
        peso = avaliacao.peso or 1.0
        total_pontos += valor * peso
        total_peso += peso

    if not tem_nota or total_peso == 0:
        return None
    return round(total_pontos / total_peso, 2)


def calcular_media_aluno(aluno: AlunoDisciplina, disciplina_id: int) -> float | None:
    """Média ponderada das avaliações de unidade (exclui Rec.).

    Preferir media_ponderada_de_mapas em listagens para evitar N+1.
    """
    avaliacoes = (
        Avaliacao.query.filter_by(disciplina_id=disciplina_id)
        .filter(Avaliacao.coluna_sigaa != Avaliacao.COLUNA_REC)
        .order_by(Avaliacao.ordem)
        .all()
    )
    if not avaliacoes:
        return None

    notas = (
        Nota.query.filter(
            Nota.aluno_disciplina_id == aluno.id,
            Nota.avaliacao_id.in_([a.id for a in avaliacoes]),
        ).all()
    )
    notas_map = {(n.aluno_disciplina_id, n.avaliacao_id): n.valor for n in notas}
    return media_ponderada_de_mapas(aluno.id, avaliacoes, notas_map, excluir_rec=False)


def carregar_notas_map(disciplina_id: int) -> dict[tuple[int, int], float | None]:
    """Uma query: mapa (aluno_id, avaliacao_id) -> valor."""
    notas = (
        Nota.query.join(Avaliacao)
        .filter(Avaliacao.disciplina_id == disciplina_id)
        .all()
    )
    return {(n.aluno_disciplina_id, n.avaliacao_id): n.valor for n in notas}


def carregar_notas_objetos(disciplina_id: int) -> dict[tuple[int, int], Nota]:
    """Uma query: mapa (aluno_id, avaliacao_id) -> objeto Nota."""
    notas = (
        Nota.query.join(Avaliacao)
        .filter(Avaliacao.disciplina_id == disciplina_id)
        .all()
    )
    return {(n.aluno_disciplina_id, n.avaliacao_id): n for n in notas}
