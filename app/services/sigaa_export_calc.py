"""Cálculos de notas no formato SIGAA (Unid. 1 / Unid. 2 / Rec. / Resultado)."""
from app.models import AlunoDisciplina, Avaliacao

COLUNAS_NOTAS_SIGAA = (
    Avaliacao.COLUNA_UNID1,
    Avaliacao.COLUNA_UNID2,
    Avaliacao.COLUNA_REC,
)

# Média das unidades abaixo deste valor → aluno vai para recuperação
LIMITE_RECUPERACAO = 7.0


def media_ponderada_coluna(
    aluno_id: int,
    avaliacoes: list[Avaliacao],
    notas_por_aluno: dict[int, dict[int, float | None]],
) -> float | None:
    """Média ponderada das avaliações mapeadas para uma coluna SIGAA."""
    total_peso = 0.0
    total_pontos = 0.0
    tem_nota = False

    for avaliacao in avaliacoes:
        valor = notas_por_aluno.get(aluno_id, {}).get(avaliacao.id)
        if valor is None:
            continue
        tem_nota = True
        peso = avaliacao.peso or 1.0
        total_pontos += valor * peso
        total_peso += peso

    if not tem_nota or total_peso == 0:
        return None
    return round(total_pontos / total_peso, 2)


def media_unidades(unid1: float | None, unid2: float | None) -> float | None:
    valores = [v for v in (unid1, unid2) if v is not None]
    if not valores:
        return None
    return round(sum(valores) / len(valores), 2)


def aluno_em_recuperacao(media_unids: float | None) -> bool:
    """Recuperação só entra se a média das unidades estiver abaixo do limite."""
    return media_unids is not None and media_unids < LIMITE_RECUPERACAO


def calcular_resultado(
    unid1: float | None,
    unid2: float | None,
    rec: float | None,
) -> float | None:
    """
    Resultado = média de Unid. 1 e Unid. 2.
    Se o aluno está em recuperação (média < 7) e tem nota de Rec.,
    Resultado = (média das unidades + Rec.) / 2.
    Caso contrário, Rec. é ignorada no Resultado.
    """
    media = media_unidades(unid1, unid2)
    if media is None:
        return None
    if aluno_em_recuperacao(media) and rec is not None:
        return round((media + rec) / 2, 2)
    return media


def calcular_notas_sigaa(
    aluno: AlunoDisciplina,
    avaliacoes_por_coluna: dict[str, list[Avaliacao]],
    notas_por_aluno: dict[int, dict[int, float | None]],
) -> dict:
    """Retorna Unid. 1, Unid. 2, Rec. e Resultado para um aluno."""
    unid1 = media_ponderada_coluna(
        aluno.id, avaliacoes_por_coluna.get(Avaliacao.COLUNA_UNID1, []), notas_por_aluno
    )
    unid2 = media_ponderada_coluna(
        aluno.id, avaliacoes_por_coluna.get(Avaliacao.COLUNA_UNID2, []), notas_por_aluno
    )
    rec_calculada = media_ponderada_coluna(
        aluno.id, avaliacoes_por_coluna.get(Avaliacao.COLUNA_REC, []), notas_por_aluno
    )

    media = media_unidades(unid1, unid2)
    em_rec = aluno_em_recuperacao(media)
    # Só exporta Rec. se o aluno de fato foi para recuperação
    rec_exportada = rec_calculada if em_rec else None
    resultado = calcular_resultado(unid1, unid2, rec_calculada)

    return {
        Avaliacao.COLUNA_UNID1: unid1,
        Avaliacao.COLUNA_UNID2: unid2,
        Avaliacao.COLUNA_REC: rec_exportada,
        "Resultado": resultado,
        "em_recuperacao": em_rec,
    }
