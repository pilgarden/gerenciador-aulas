"""Geração de PDF de listas (notas / faltas) para envio aos alunos."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models import AlunoDisciplina, Avaliacao, Disciplina, Usuario
from app.services.academico import carregar_notas_map, media_ponderada_de_mapas
from app.services.estatisticas import calcular_estatisticas


STATIC_IMG = Path(__file__).resolve().parents[1] / "static" / "img"

CABECALHO_UNIR_LINHAS = (
    "UNIVERSIDADE FEDERAL DE RONDÔNIA (UNIR)",
    "Faculdade de Engenharia, Tecnologia e Inovação (FAETI)",
    "Bacharelado em Engenharia Civil — Porto Velho/RO",
)


@dataclass
class RelatorioConfig:
    tipo: str  # notas | faltas | ambos
    matricula_modo: str  # completa | parcial
    digitos_matricula: int = 4
    incluir_nome: bool = True
    incluir_media: bool = True
    avaliacao_ids: list[int] = field(default_factory=list)
    usar_cabecalho_unir: bool = False
    titulo_custom: str = ""
    linha1: str = ""
    linha2: str = ""
    linha3: str = ""


def mascarar_matricula(matricula: str, modo: str, digitos: int) -> str:
    matricula = (matricula or "").strip()
    if modo != "parcial":
        return matricula
    digitos = max(1, min(digitos, len(matricula) or 1))
    if len(matricula) <= digitos:
        return matricula
    return "*" * (len(matricula) - digitos) + matricula[-digitos:]


def _logo_path(nome: str) -> Path | None:
    for candidate in (STATIC_IMG / f"{nome}_transp.png", STATIC_IMG / f"{nome}.png"):
        if candidate.exists():
            return candidate
    return None


def _styles():
    base = getSampleStyleSheet()
    return {
        "inst": ParagraphStyle(
            "inst",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#1a3a6b"),
        ),
        "sub": ParagraphStyle(
            "sub",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#333333"),
        ),
        "disc": ParagraphStyle(
            "disc",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#000000"),
            spaceBefore=4,
            spaceAfter=2,
        ),
        "meta": ParagraphStyle(
            "meta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#444444"),
        ),
        "titulo": ParagraphStyle(
            "titulo",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=14,
            alignment=TA_CENTER,
            spaceBefore=8,
            spaceAfter=8,
        ),
        "cell": ParagraphStyle(
            "cell",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_LEFT,
        ),
        "cell_c": ParagraphStyle(
            "cell_c",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
        ),
        "th": ParagraphStyle(
            "th",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
        ),
        "assinatura": ParagraphStyle(
            "assinatura",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#222222"),
        ),
        "assinatura_meta": ParagraphStyle(
            "assinatura_meta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#555555"),
        ),
    }


class LogoImage(Flowable):
    """Imagem com tamanho fixo (evita bug de altura do ReportLab com PNG/RGBA)."""

    def __init__(self, path: Path, width, height):
        super().__init__()
        from PIL import Image as PILImage

        im = PILImage.open(path).convert("RGBA")
        bg = PILImage.new("RGB", im.size, (255, 255, 255))
        bg.paste(im, mask=im.split()[3])
        self._buf = BytesIO()
        bg.save(self._buf, format="PNG")
        self._buf.seek(0)
        self.drawWidth = float(width)
        self.drawHeight = float(height)

    def wrap(self, availWidth, availHeight):
        return self.drawWidth, self.drawHeight

    def draw(self):
        self._buf.seek(0)
        self.canv.drawImage(
            ImageReader(self._buf),
            0,
            0,
            width=self.drawWidth,
            height=self.drawHeight,
            mask="auto",
            preserveAspectRatio=True,
            anchor="c",
        )


def _image_flowable(path: Path, width, height) -> LogoImage:
    return LogoImage(path, width, height)

def _montar_cabecalho(
    styles,
    disciplina: Disciplina,
    professor: Usuario,
    config: RelatorioConfig,
    gerado_em: date,
) -> list:
    flow: list = []
    logo_unir = _logo_path("logo_unir")
    logo_civil = _logo_path("logo_eng_civil")

    if config.usar_cabecalho_unir and professor.acesso_cabecalho_unir:
        left = (
            _image_flowable(logo_unir, 2.2 * cm, 1.9 * cm)
            if logo_unir
            else Spacer(1, 1)
        )
        right = (
            _image_flowable(logo_civil, 2.0 * cm, 2.0 * cm)
            if logo_civil
            else Spacer(1, 1)
        )
        texto = Paragraph(
            "<br/>".join(
                [
                    f"<b>{CABECALHO_UNIR_LINHAS[0]}</b>",
                    CABECALHO_UNIR_LINHAS[1],
                    CABECALHO_UNIR_LINHAS[2],
                ]
            ),
            styles["sub"],
        )
        header_table = Table(
            [[left, texto, right]],
            colWidths=[2.6 * cm, 12.3 * cm, 2.6 * cm],
        )
        header_table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("ALIGN", (0, 0), (0, 0), "CENTER"),
                    ("ALIGN", (2, 0), (2, 0), "CENTER"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ]
            )
        )
        flow.append(header_table)
    else:
        linhas = [
            config.linha1.strip() or "Relatório acadêmico",
            config.linha2.strip(),
            config.linha3.strip(),
        ]
        for i, linha in enumerate(linhas):
            if not linha:
                continue
            flow.append(Paragraph(linha, styles["inst"] if i == 0 else styles["sub"]))

    flow.append(
        Paragraph(
            f"{disciplina.codigo} — {disciplina.nome} (Turma {disciplina.turma})",
            styles["disc"],
        )
    )
    flow.append(Paragraph(f"Semestre {disciplina.semestre.codigo}", styles["meta"]))
    flow.append(Spacer(1, 3 * mm))
    return flow


def _bloco_assinatura(styles, professor: Usuario, gerado_em: date) -> list:
    tratamento = (professor.tratamento or "Prof.").strip()
    return [
        Spacer(1, 18 * mm),
        Paragraph("_______________________________", styles["assinatura_meta"]),
        Spacer(1, 2 * mm),
        Paragraph(f"{tratamento} {professor.nome}", styles["assinatura"]),
        Paragraph(professor.email, styles["assinatura_meta"]),
        Paragraph(
            f"Relatório gerado em {gerado_em.strftime('%d/%m/%Y')}",
            styles["assinatura_meta"],
        ),
    ]

def _fmt_nota(valor: float | None) -> str:
    if valor is None:
        return "—"
    if abs(valor - round(valor)) < 1e-9:
        return str(int(round(valor)))
    return f"{valor:.2f}".replace(".", ",")


def gerar_pdf_relatorio(
    disciplina: Disciplina,
    professor: Usuario,
    config: RelatorioConfig,
    gerado_em: date | None = None,
) -> bytes:
    gerado_em = gerado_em or date.today()
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=1.2 * cm,
        bottomMargin=1.5 * cm,
        title=f"Relatório {disciplina.codigo}",
    )

    alunos = disciplina.alunos.order_by(AlunoDisciplina.nome).all()
    avaliacoes = disciplina.avaliacoes.order_by(Avaliacao.ordem).all()
    if config.avaliacao_ids:
        ids = set(config.avaliacao_ids)
        avaliacoes = [a for a in avaliacoes if a.id in ids]

    notas_map = carregar_notas_map(disciplina.id) if config.tipo in ("notas", "ambos") else {}
    faltas_map: dict[int, int] = {}
    if config.tipo in ("faltas", "ambos"):
        stats = calcular_estatisticas(disciplina)
        faltas_map = {s.aluno.id: s.faltas for s in stats.alunos_frequencia}

    story = _montar_cabecalho(styles, disciplina, professor, config, gerado_em)

    if config.titulo_custom.strip():
        titulo = config.titulo_custom.strip()
    elif config.tipo == "notas":
        titulo = "Lista de notas"
    elif config.tipo == "faltas":
        titulo = "Lista de faltas"
    else:
        titulo = "Lista de notas e faltas"
    story.append(Paragraph(titulo, styles["titulo"]))

    headers = [Paragraph("Matrícula", styles["th"])]
    col_widths = [3.2 * cm]
    if config.incluir_nome:
        headers.append(Paragraph("Nome", styles["th"]))
        col_widths.append(6.5 * cm if config.tipo == "faltas" else 4.5 * cm)

    if config.tipo in ("notas", "ambos"):
        for av in avaliacoes:
            headers.append(Paragraph(av.nome, styles["th"]))
            col_widths.append(1.6 * cm)
        if config.incluir_media:
            headers.append(Paragraph("Média", styles["th"]))
            col_widths.append(1.5 * cm)

    if config.tipo in ("faltas", "ambos"):
        headers.append(Paragraph("Faltas", styles["th"]))
        col_widths.append(1.5 * cm)

    # Ajusta larguras se estourar
    total = sum(col_widths)
    page_w = A4[0] - 3 * cm
    if total > page_w:
        scale = page_w / total
        col_widths = [w * scale for w in col_widths]

    data = [headers]
    for aluno in alunos:
        row = [
            Paragraph(
                mascarar_matricula(aluno.matricula, config.matricula_modo, config.digitos_matricula),
                styles["cell_c"],
            )
        ]
        if config.incluir_nome:
            row.append(Paragraph(aluno.nome, styles["cell"]))
        if config.tipo in ("notas", "ambos"):
            for av in avaliacoes:
                row.append(
                    Paragraph(
                        _fmt_nota(notas_map.get((aluno.id, av.id))),
                        styles["cell_c"],
                    )
                )
            if config.incluir_media:
                media = media_ponderada_de_mapas(aluno.id, avaliacoes, notas_map)
                row.append(Paragraph(_fmt_nota(media), styles["cell_c"]))
        if config.tipo in ("faltas", "ambos"):
            row.append(Paragraph(str(faltas_map.get(aluno.id, 0)), styles["cell_c"]))
        data.append(row)

    table = Table(data, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef5")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#aaaaaa")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LEFTPADDING", (0, 0), (-1, -1), 3),
                ("RIGHTPADDING", (0, 0), (-1, -1), 3),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f7f9fc")]),
            ]
        )
    )
    story.append(table)
    story.extend(_bloco_assinatura(styles, professor, gerado_em))

    def _footer(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#666666"))
        canvas.drawCentredString(
            A4[0] / 2,
            0.8 * cm,
            f"Página {doc_.page} — {disciplina.codigo} T{disciplina.turma}",
        )
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buffer.getvalue()


def nome_arquivo_relatorio(disciplina: Disciplina, tipo: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d")
    return f"lista_{tipo}_{disciplina.codigo}_T{disciplina.turma}_{stamp}.pdf"
