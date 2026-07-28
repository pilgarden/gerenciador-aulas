"""Testes do mapeamento de colunas SIGAA."""
from app.models import Avaliacao
from app.services.sigaa_colunas import detectar_coluna_sigaa


def test_detectar_coluna_sigaa():
    assert detectar_coluna_sigaa("Unid. 1") == Avaliacao.COLUNA_UNID1
    assert detectar_coluna_sigaa("Unid. 2") == Avaliacao.COLUNA_UNID2
    assert detectar_coluna_sigaa("Rec.") == Avaliacao.COLUNA_REC
    assert detectar_coluna_sigaa("Prova 1") == Avaliacao.COLUNA_UNID1
    assert detectar_coluna_sigaa("Trabalho unidade 2") == Avaliacao.COLUNA_UNID2
