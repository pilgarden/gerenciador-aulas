"""Parser de planilhas de notas exportadas pelo SIGAA."""
import re
from dataclasses import dataclass, field
from io import BytesIO

import pandas as pd


DISCIPLINA_RE = re.compile(
    r"^(?P<codigo>\S+)\s*-\s*(?P<nome>.+?)\s*\((?P<ch>\d+)h\)\s*-\s*Turma:\s*(?P<turma>\S+)\s*\((?P<semestre>[\d.]+)\)\s*$",
    re.IGNORECASE,
)


@dataclass
class AlunoImportado:
    matricula: str
    nome: str
    faltas: int = 0
    situacao: str | None = None
    notas: dict[str, str | float | None] = field(default_factory=dict)


@dataclass
class SigaaImportResult:
    codigo: str
    nome: str
    turma: str
    semestre: str
    carga_horaria: int | None
    colunas_notas: list[str]
    alunos: list[AlunoImportado]
    erros: list[str] = field(default_factory=list)


class SigaaImportError(Exception):
    pass


def _normalize(value):
    if pd.isna(value):
        return None
    text = str(value).strip()
    return text if text else None


def _parse_nota(value):
    text = _normalize(value)
    if text is None or text == "-":
        return None
    text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return text


def _parse_int(value, default=0):
    text = _normalize(value)
    if text is None or text == "-":
        return default
    try:
        return int(float(text.replace(",", ".")))
    except ValueError:
        return default


def _find_disciplina_row(df: pd.DataFrame) -> tuple[int, str] | None:
    for idx, row in df.iterrows():
        for cell in row:
            text = _normalize(cell)
            if text and DISCIPLINA_RE.match(text):
                return idx, text
    return None


def _find_header_row(df: pd.DataFrame, start: int = 0) -> tuple[int, dict[int, str]] | None:
    for idx in range(start, len(df)):
        row = df.iloc[idx]
        columns: dict[int, str] = {}
        for col_idx, cell in enumerate(row):
            text = _normalize(cell)
            if text:
                columns[col_idx] = text
        labels = {v.lower() for v in columns.values()}
        if "matrícula" in labels or "matricula" in labels:
            return idx, columns
    return None


def parse_sigaa_xls(file_bytes: bytes) -> SigaaImportResult:
    try:
        df = pd.read_excel(BytesIO(file_bytes), header=None, engine="xlrd")
    except Exception as exc:
        raise SigaaImportError(f"Arquivo inválido ou corrompido: {exc}") from exc
    erros: list[str] = []

    disciplina_info = _find_disciplina_row(df)
    if not disciplina_info:
        raise SigaaImportError(
            "Não foi possível identificar a disciplina na planilha. "
            "Verifique se é uma planilha de notas exportada pelo SIGAA."
        )

    _, disciplina_text = disciplina_info
    match = DISCIPLINA_RE.match(disciplina_text)
    if not match:
        raise SigaaImportError(f"Formato da disciplina não reconhecido: {disciplina_text}")

    header_info = _find_header_row(df, start=disciplina_info[0])
    if not header_info:
        raise SigaaImportError("Cabeçalho com coluna 'Matrícula' não encontrado.")

    header_idx, columns = header_info
    col_map = {name.lower(): idx for idx, name in columns.items()}

    matricula_col = col_map.get("matrícula") or col_map.get("matricula")
    nome_col = col_map.get("nome")
    faltas_col = col_map.get("faltas")
    situacao_col = col_map.get("sit.") or col_map.get("sit")

    if matricula_col is None or nome_col is None:
        raise SigaaImportError("Colunas obrigatórias 'Matrícula' e 'Nome' não encontradas.")

    nota_cols: dict[int, str] = {}
    for idx, label in columns.items():
        lower = label.lower()
        if idx in (matricula_col, nome_col, faltas_col, situacao_col):
            continue
        if lower in ("resultado",):
            continue
        nota_cols[idx] = label

    alunos: list[AlunoImportado] = []
    for idx in range(header_idx + 1, len(df)):
        row = df.iloc[idx]
        matricula = _normalize(row.iloc[matricula_col])
        nome = _normalize(row.iloc[nome_col])
        if not matricula or not nome:
            continue
        if not str(matricula).isdigit():
            erros.append(f"Linha {idx + 1}: matrícula inválida '{matricula}'.")
            continue

        notas = {label: _parse_nota(row.iloc[col_idx]) for col_idx, label in nota_cols.items()}
        alunos.append(
            AlunoImportado(
                matricula=str(matricula),
                nome=nome,
                faltas=_parse_int(row.iloc[faltas_col]) if faltas_col is not None else 0,
                situacao=_normalize(row.iloc[situacao_col]) if situacao_col is not None else None,
                notas=notas,
            )
        )

    if not alunos:
        raise SigaaImportError("Nenhum aluno encontrado na planilha.")

    return SigaaImportResult(
        codigo=match.group("codigo"),
        nome=match.group("nome").strip(),
        turma=match.group("turma"),
        semestre=match.group("semestre"),
        carga_horaria=int(match.group("ch")),
        colunas_notas=list(nota_cols.values()),
        alunos=alunos,
        erros=erros,
    )


def import_result_to_dict(result: SigaaImportResult) -> dict:
    return {
        "codigo": result.codigo,
        "nome": result.nome,
        "turma": result.turma,
        "semestre": result.semestre,
        "carga_horaria": result.carga_horaria,
        "colunas_notas": result.colunas_notas,
        "erros": result.erros,
        "alunos": [
            {
                "matricula": a.matricula,
                "nome": a.nome,
                "faltas": a.faltas,
                "situacao": a.situacao,
                "notas": a.notas,
            }
            for a in result.alunos
        ],
    }


def import_result_from_dict(data: dict) -> SigaaImportResult:
    return SigaaImportResult(
        codigo=data["codigo"],
        nome=data["nome"],
        turma=data["turma"],
        semestre=data["semestre"],
        carga_horaria=data.get("carga_horaria"),
        colunas_notas=data.get("colunas_notas", []),
        erros=data.get("erros", []),
        alunos=[
            AlunoImportado(
                matricula=a["matricula"],
                nome=a["nome"],
                faltas=a.get("faltas", 0),
                situacao=a.get("situacao"),
                notas=a.get("notas", {}),
            )
            for a in data["alunos"]
        ],
    )
