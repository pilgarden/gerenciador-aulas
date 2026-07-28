"""Geração de planilhas compatíveis com reimportação no SIGAA.

A exportação SEMPRE usa o formato fixo do SIGAA:
Matrícula | Nome | Unid. 1 | Unid. 2 | Rec. | Resultado | Faltas | Sit.

As avaliações internas do semestre (provas, trabalhos, etc.) são agregadas
por média ponderada na coluna SIGAA correspondente (coluna_sigaa).
"""
from io import BytesIO

import xlwt

from app.models import AlunoDisciplina, Avaliacao, Disciplina, Nota
from app.services.academico import contar_faltas_aluno

INSTRUCOES = [
    "Digite as notas das unidades utilizando vírgula para separar a casa decimal.",
    "O campo faltas deve ser preenchido com o número de faltas do aluno durante o período letivo.",
    "A situação do aluno em relação a assiduidade é calculada apenas levando em consideração a carga horária da disciplina.",
    "Devido a isso a situação pode mudar durante a importação da planilha.",
    "As notas das unidades não vão para o histórico do aluno, no entanto, aparecem em seu portal.",
    "Altere somente as células em amarelo.",
]

COLUNAS_NOTAS_SIGAA = (
    Avaliacao.COLUNA_UNID1,
    Avaliacao.COLUNA_UNID2,
    Avaliacao.COLUNA_REC,
)

# Média das unidades abaixo deste valor → aluno vai para recuperação
LIMITE_RECUPERACAO = 7.0


def _formatar_nota(valor: float | None) -> str:
    if valor is None:
        return "-"
    texto = f"{valor:.2f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


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
) -> dict[str, float | None]:
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


def gerar_planilha_sigaa(disciplina: Disciplina) -> bytes:
    semestre = disciplina.semestre
    ch = disciplina.carga_horaria or 0
    titulo_disciplina = (
        f"{disciplina.codigo} - {disciplina.nome} ({ch}h) - "
        f"Turma: {disciplina.turma} ({semestre.codigo})"
    )

    avaliacoes = disciplina.avaliacoes.order_by(Avaliacao.ordem).all()
    alunos = disciplina.alunos.order_by(AlunoDisciplina.nome).all()

    avaliacoes_por_coluna: dict[str, list[Avaliacao]] = {c: [] for c in COLUNAS_NOTAS_SIGAA}
    for av in avaliacoes:
        coluna = av.coluna_sigaa if av.coluna_sigaa in COLUNAS_NOTAS_SIGAA else Avaliacao.COLUNA_UNID1
        avaliacoes_por_coluna[coluna].append(av)

    notas_por_aluno: dict[int, dict[int, float | None]] = {}
    for nota in Nota.query.join(Avaliacao).filter(Avaliacao.disciplina_id == disciplina.id).all():
        notas_por_aluno.setdefault(nota.aluno_disciplina_id, {})[nota.avaliacao_id] = nota.valor

    workbook = xlwt.Workbook(encoding="utf-8")
    sheet = workbook.add_sheet("Planilha")

    sheet.write(1, 1, "PLANILHA DE NOTAS")
    sheet.write(2, 1, titulo_disciplina)

    for i, texto in enumerate(INSTRUCOES):
        sheet.write(4 + i, 1, texto)

    # Cabeçalho fixo do SIGAA (coluna B em diante)
    header_row = 10
    headers = [
        "Matrícula",
        "Nome",
        Avaliacao.COLUNA_UNID1,
        Avaliacao.COLUNA_UNID2,
        Avaliacao.COLUNA_REC,
        "Resultado",
        "Faltas",
        "Sit.",
    ]
    for col_idx, label in enumerate(headers, start=1):
        sheet.write(header_row, col_idx, label)

    for row_idx, aluno in enumerate(alunos, start=header_row + 1):
        notas_sigaa = calcular_notas_sigaa(aluno, avaliacoes_por_coluna, notas_por_aluno)
        faltas = contar_faltas_aluno(aluno)
        if faltas == 0:
            faltas = aluno.faltas_sigaa or 0

        sheet.write(row_idx, 1, aluno.matricula)
        sheet.write(row_idx, 2, aluno.nome)
        sheet.write(row_idx, 3, _formatar_nota(notas_sigaa[Avaliacao.COLUNA_UNID1]))
        sheet.write(row_idx, 4, _formatar_nota(notas_sigaa[Avaliacao.COLUNA_UNID2]))
        sheet.write(row_idx, 5, _formatar_nota(notas_sigaa[Avaliacao.COLUNA_REC]))
        resultado = notas_sigaa["Resultado"]
        sheet.write(row_idx, 6, resultado if resultado is not None else 0)
        sheet.write(row_idx, 7, faltas)
        sheet.write(row_idx, 8, aluno.situacao or 0)

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def nome_arquivo_exportacao(disciplina: Disciplina) -> str:
    semestre = disciplina.semestre.codigo.replace(".", "")
    turma = disciplina.turma.zfill(2)
    return f"notas_{disciplina.codigo}_T{turma}_{semestre}.xls"
