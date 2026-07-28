"""Testes do parser SIGAA."""
from pathlib import Path

import pytest

from app.services.sigaa_import import (
    SigaaImportError,
    import_result_from_dict,
    import_result_to_dict,
    parse_sigaa_xls,
)

SIGAA_SAMPLE = Path(r"c:\Users\Pedro\Downloads\notas_DEC10058_T01_20262.xls.xls")


@pytest.mark.skipif(not SIGAA_SAMPLE.exists(), reason="Planilha SIGAA de exemplo não encontrada")
def test_parse_sigaa_sample():
    result = parse_sigaa_xls(SIGAA_SAMPLE.read_bytes())
    assert result.codigo == "DEC10058"
    assert "ELEMENTOS FINITOS" in result.nome.upper()
    assert result.turma == "01"
    assert result.semestre == "2026.2"
    assert result.carga_horaria == 60
    assert len(result.alunos) >= 1
    assert result.alunos[0].matricula.isdigit()
    assert "Unid. 1" in result.colunas_notas


def test_parse_sigaa_invalid():
    with pytest.raises(SigaaImportError):
        parse_sigaa_xls(b"invalid")


def test_import_result_roundtrip():
    from app.services.sigaa_import import AlunoImportado, SigaaImportResult

    original = SigaaImportResult(
        codigo="DEC10058",
        nome="Teste",
        turma="01",
        semestre="2026.2",
        carga_horaria=60,
        colunas_notas=["Unid. 1"],
        alunos=[AlunoImportado(matricula="123", nome="Aluno Teste", notas={"Unid. 1": 8.5})],
    )
    restored = import_result_from_dict(import_result_to_dict(original))
    assert restored.codigo == original.codigo
    assert restored.alunos[0].nome == "Aluno Teste"
    assert restored.alunos[0].notas["Unid. 1"] == 8.5
