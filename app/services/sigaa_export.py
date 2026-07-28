"""Geração de planilhas no formato idêntico ao SIGAA.

Estrutura do arquivo original (confirmada por análise BIFF):
- Aba: Sheet0
- Sem fórmulas Excel (Resultado é valor numérico calculado)
- Células mescladas nas linhas de título/instruções (B–I)
- Cabeçalho na linha 12 (índice 11): Matrícula | Nome | Unid. 1 | Unid. 2 | Rec. | Resultado | Faltas | Sit.
- Células editáveis (Unid. 1, Unid. 2, Rec., Faltas) com fundo amarelo (#FFFF99)
- Cabeçalho com fundo cinza (#C0C0C0)
- Notas vazias como texto '-'; notas preenchidas como texto com vírgula decimal
- Resultado: número formato 0.0; Faltas: número formato 0; Sit.: número
"""
from io import BytesIO

import xlwt

from app.models import AlunoDisciplina, Avaliacao, Disciplina, Nota
from app.services.academico import contar_faltas_aluno
from app.services.sigaa_export_calc import (
    COLUNAS_NOTAS_SIGAA,
    calcular_notas_sigaa,
)

# Reexporta helpers usados pelos testes
from app.services.sigaa_export_calc import (  # noqa: F401
    LIMITE_RECUPERACAO,
    aluno_em_recuperacao,
    calcular_resultado,
    media_ponderada_coluna,
    media_unidades,
)

INSTRUCOES = [
    "Digite as notas das unidades utilizando vírgula para separar a casa decimal.",
    "O campo faltas deve ser preenchido com o número de faltas do aluno durante o período letivo.",
    "A situação do aluno em relação a assiduidade é calculada apenas levando em consideração a carga horária da disciplina.",
    "Devido a isso a situação pode mudar durante a importação da planilha.",
    "As notas das unidades não vão para o histórico do aluno, no entanto, aparecem em seu portal.",
    "Altere somente as células em amarelo.",
]


def _formatar_nota_texto(valor: float | None) -> str:
    """SIGAA espera texto com vírgula; vazio = '-'."""
    if valor is None:
        return "-"
    texto = f"{valor:.2f}".rstrip("0").rstrip(".")
    return texto.replace(".", ",")


_PALETTE_READY = False


def _ensure_palette():
    global _PALETTE_READY
    if _PALETTE_READY:
        return
    xlwt.add_palette_colour("sigaa_yellow", 0x21)
    xlwt.add_palette_colour("sigaa_gray", 0x22)
    _PALETTE_READY = True


def _styles():
    """Estilos aproximados ao arquivo original do SIGAA."""
    _ensure_palette()
    easy = xlwt.easyxf
    title = easy("font: name Arial, height 200; align: vert centre")
    header = easy(
        "font: name Arial, height 200; "
        "align: horiz centre, vert centre; "
        "pattern: pattern solid, fore_colour sigaa_gray; "
        "borders: left hair, right hair, top hair, bottom hair"
    )
    # Células de dados (não amarelas)
    data = easy(
        "font: name Arial, height 200; align: vert centre; "
        "borders: left hair, right hair, top hair, bottom hair"
    )
    # Notas editáveis (amarelo) — texto
    nota_amarela = easy(
        "font: name Arial, height 200; align: vert centre; "
        "pattern: pattern solid, fore_colour sigaa_yellow; "
        "borders: left hair, right hair, top hair, bottom hair"
    )
    # Resultado numérico 0.0
    resultado = easy(
        "font: name Arial, height 200; align: vert centre; "
        "borders: left hair, right hair, top hair, bottom hair",
        num_format_str="0.0",
    )
    # Faltas editáveis (amarelo) — inteiro
    faltas = easy(
        "font: name Arial, height 200; align: vert centre; "
        "pattern: pattern solid, fore_colour sigaa_yellow; "
        "borders: left hair, right hair, top hair, bottom hair",
        num_format_str="0",
    )
    # Sit. numérico
    situacao = easy(
        "font: name Arial, height 200; align: vert centre; "
        "borders: left hair, right hair, top hair, bottom hair"
    )
    # Moldura laterais / vazios
    borda_esq = easy("borders: right thin; align: vert centre")
    borda_dir = easy("borders: left thin; align: vert centre")
    borda_topo = easy("borders: bottom thin; align: vert centre")
    borda_base = easy("borders: top thin; align: vert centre")
    vazio = easy("align: vert centre")
    sep_header = easy("borders: top thin, bottom thin; align: vert centre")

    return {
        "title": title,
        "header": header,
        "data": data,
        "nota_amarela": nota_amarela,
        "resultado": resultado,
        "faltas": faltas,
        "situacao": situacao,
        "borda_esq": borda_esq,
        "borda_dir": borda_dir,
        "borda_topo": borda_topo,
        "borda_base": borda_base,
        "vazio": vazio,
        "sep_header": sep_header,
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
    # Palette: amarelo SIGAA #FFFF99, cinza #C0C0C0
    workbook.set_colour_RGB(0x21, 255, 255, 153)
    workbook.set_colour_RGB(0x22, 192, 192, 192)

    sheet = workbook.add_sheet("Sheet0")
    st = _styles()

    # Larguras como no original (unidades xlwt ≈ 1/256 do caractere)
    widths = [768, 3840, 8762, 1536, 1536, 1536, 2560, 1536, 1536, 768]
    for col, width in enumerate(widths):
        sheet.col(col).width = width

    # Linha 0: borda superior
    for c in range(1, 9):
        sheet.write(0, c, "", st["borda_topo"])

    # Linhas 1–9: título + instruções (mescladas B–I)
    sheet.write_merge(1, 1, 1, 8, "PLANILHA DE NOTAS", st["title"])
    sheet.write_merge(2, 2, 1, 8, titulo_disciplina, st["title"])
    sheet.write_merge(3, 3, 1, 8, "", st["title"])
    for i, texto in enumerate(INSTRUCOES):
        sheet.write_merge(4 + i, 4 + i, 1, 8, texto, st["title"])

    # Laterais da moldura (col A e J) nas linhas de título
    for r in range(1, 10):
        sheet.write(r, 0, "", st["borda_esq"])
        sheet.write(r, 9, "", st["borda_dir"])

    # Linha 10: separador antes do cabeçalho
    for c in range(1, 9):
        sheet.write(10, c, "", st["sep_header"])

    # Linha 11: cabeçalho fixo SIGAA
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
    sheet.write(11, 0, "", st["borda_esq"])
    for col_idx, label in enumerate(headers, start=1):
        sheet.write(11, col_idx, label, st["header"])
    sheet.write(11, 9, "", st["borda_dir"])

    # Dados dos alunos (a partir da linha 12)
    for offset, aluno in enumerate(alunos):
        row = 12 + offset
        notas_sigaa = calcular_notas_sigaa(aluno, avaliacoes_por_coluna, notas_por_aluno)
        faltas = contar_faltas_aluno(aluno)
        if faltas == 0:
            faltas = aluno.faltas_sigaa or 0

        sit_val = aluno.situacao
        try:
            sit_num = float(sit_val) if sit_val not in (None, "") else 0
        except (TypeError, ValueError):
            sit_num = 0

        resultado = notas_sigaa["Resultado"]

        sheet.write(row, 0, "", st["borda_esq"])
        sheet.write(row, 1, aluno.matricula, st["data"])
        sheet.write(row, 2, aluno.nome, st["data"])
        sheet.write(row, 3, _formatar_nota_texto(notas_sigaa[Avaliacao.COLUNA_UNID1]), st["nota_amarela"])
        sheet.write(row, 4, _formatar_nota_texto(notas_sigaa[Avaliacao.COLUNA_UNID2]), st["nota_amarela"])
        sheet.write(row, 5, _formatar_nota_texto(notas_sigaa[Avaliacao.COLUNA_REC]), st["nota_amarela"])
        sheet.write(row, 6, float(resultado) if resultado is not None else 0.0, st["resultado"])
        sheet.write(row, 7, int(faltas), st["faltas"])
        sheet.write(row, 8, sit_num, st["situacao"])
        sheet.write(row, 9, "", st["borda_dir"])

    # Linha final (borda inferior), como no original
    last = 12 + len(alunos)
    for c in range(1, 9):
        sheet.write(last, c, "", st["borda_base"])

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def nome_arquivo_exportacao(disciplina: Disciplina) -> str:
    semestre = disciplina.semestre.codigo.replace(".", "")
    turma = disciplina.turma.zfill(2)
    return f"notas_{disciplina.codigo}_T{turma}_{semestre}.xls"
