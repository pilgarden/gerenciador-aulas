"""Geração de planilhas compatíveis com reimportação no SIGAA."""
from io import BytesIO

import xlwt

from app.models import AlunoDisciplina, Avaliacao, Disciplina, Nota
from app.services.academico import calcular_media_aluno, contar_faltas_aluno

INSTRUCOES = [
    "Digite as notas das unidades utilizando vírgula para separar a casa decimal.",
    "O campo faltas deve ser preenchido com o número de faltas do aluno durante o período letivo.",
    "A situação do aluno em relação a assiduidade é calculada apenas levando em consideração a carga horária da disciplina.",
    "Devido a isso a situação pode mudar durante a importação da planilha.",
    "As notas das unidades não vão para o histórico do aluno, no entanto, aparecem em seu portal.",
    "Altere somente as células em amarelo.",
]


def _formatar_nota(valor: float | None) -> str:
    if valor is None:
        return "-"
    texto = f"{valor:.2f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


def _formatar_numero(valor: int | float | None, default=0) -> int | float:
    if valor is None:
        return default
    return valor


def gerar_planilha_sigaa(disciplina: Disciplina) -> bytes:
    semestre = disciplina.semestre
    ch = disciplina.carga_horaria or 0
    titulo_disciplina = (
        f"{disciplina.codigo} - {disciplina.nome} ({ch}h) - "
        f"Turma: {disciplina.turma} ({semestre.codigo})"
    )

    avaliacoes = disciplina.avaliacoes.order_by(Avaliacao.ordem).all()
    alunos = disciplina.alunos.order_by(AlunoDisciplina.nome).all()

    workbook = xlwt.Workbook(encoding="utf-8")
    sheet = workbook.add_sheet("Planilha")

    # Coluna A vazia; dados a partir da coluna B (índice 1), como no SIGAA
    sheet.write(1, 1, "PLANILHA DE NOTAS")
    sheet.write(2, 1, titulo_disciplina)

    for i, texto in enumerate(INSTRUCOES):
        sheet.write(4 + i, 1, texto)

    header_row = 10
    col = 1
    sheet.write(header_row, col, "Matrícula")
    col += 1
    sheet.write(header_row, col, "Nome")
    col += 1

    for avaliacao in avaliacoes:
        sheet.write(header_row, col, avaliacao.nome)
        col += 1

    sheet.write(header_row, col, "Resultado")
    col_resultado = col
    col += 1
    sheet.write(header_row, col, "Faltas")
    col_faltas = col
    col += 1
    sheet.write(header_row, col, "Sit.")
    col_sit = col

    notas_por_aluno: dict[int, dict[int, float | None]] = {}
    for nota in Nota.query.join(Avaliacao).filter(Avaliacao.disciplina_id == disciplina.id).all():
        notas_por_aluno.setdefault(nota.aluno_disciplina_id, {})[nota.avaliacao_id] = nota.valor

    for row_idx, aluno in enumerate(alunos, start=header_row + 1):
        col = 1
        sheet.write(row_idx, col, aluno.matricula)
        col += 1
        sheet.write(row_idx, col, aluno.nome)
        col += 1

        for avaliacao in avaliacoes:
            valor = notas_por_aluno.get(aluno.id, {}).get(avaliacao.id)
            sheet.write(row_idx, col, _formatar_nota(valor))
            col += 1

        media = calcular_media_aluno(aluno, disciplina.id)
        sheet.write(row_idx, col_resultado, _formatar_numero(media, 0))
        faltas = contar_faltas_aluno(aluno) or aluno.faltas_sigaa
        sheet.write(row_idx, col_faltas, faltas)
        sheet.write(row_idx, col_sit, aluno.situacao or 0)

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def nome_arquivo_exportacao(disciplina: Disciplina) -> str:
    semestre = disciplina.semestre.codigo.replace(".", "")
    turma = disciplina.turma.zfill(2)
    return f"notas_{disciplina.codigo}_T{turma}_{semestre}.xls"
