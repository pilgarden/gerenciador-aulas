"""Testes da regra de recuperação no Resultado SIGAA."""
from app.models import Avaliacao
from app.services.sigaa_export_calc import (
    aluno_em_recuperacao,
    calcular_notas_sigaa,
    calcular_resultado,
)


def test_resultado_sem_recuperacao():
    # Média 8 >= 7 → Rec. ignorada
    assert calcular_resultado(8.0, 8.0, 10.0) == 8.0
    assert aluno_em_recuperacao(8.0) is False


def test_resultado_com_recuperacao():
    # Média 6 < 7 → Resultado = (6 + 8) / 2 = 7
    assert aluno_em_recuperacao(6.0) is True
    assert calcular_resultado(5.0, 7.0, 8.0) == 7.0


def test_resultado_em_rec_sem_nota_rec():
    # Em recuperação mas sem nota de Rec. → mantém média das unidades
    assert calcular_resultado(4.0, 6.0, None) == 5.0


def test_calcular_notas_sigaa_rec_so_se_necessario():
    class FakeAluno:
        id = 1

    avaliacoes_por_coluna = {
        Avaliacao.COLUNA_UNID1: [],
        Avaliacao.COLUNA_UNID2: [],
        Avaliacao.COLUNA_REC: [],
    }
    # Sem avaliações reais: usamos médias injetadas via mock das funções
    # Teste direto da regra de exportação da coluna Rec.
    from app.services import sigaa_export_calc as mod

    original = mod.media_ponderada_coluna

    def fake_media(aluno_id, avaliacoes, notas_por_aluno):
        # Distingue pela lista vazia — usamos notas_por_aluno sentinel
        chave = notas_por_aluno.get("_modo")
        if chave == "aprovado":
            if avaliacoes is avaliacoes_por_coluna[Avaliacao.COLUNA_UNID1]:
                return 8.0
            if avaliacoes is avaliacoes_por_coluna[Avaliacao.COLUNA_UNID2]:
                return 9.0
            if avaliacoes is avaliacoes_por_coluna[Avaliacao.COLUNA_REC]:
                return 10.0
        if chave == "recuperacao":
            if avaliacoes is avaliacoes_por_coluna[Avaliacao.COLUNA_UNID1]:
                return 5.0
            if avaliacoes is avaliacoes_por_coluna[Avaliacao.COLUNA_UNID2]:
                return 5.0
            if avaliacoes is avaliacoes_por_coluna[Avaliacao.COLUNA_REC]:
                return 8.0
        return None

    mod.media_ponderada_coluna = fake_media
    try:
        aprovado = calcular_notas_sigaa(FakeAluno(), avaliacoes_por_coluna, {"_modo": "aprovado"})
        assert aprovado[Avaliacao.COLUNA_REC] is None  # não exporta Rec.
        assert aprovado["Resultado"] == 8.5
        assert aprovado["em_recuperacao"] is False

        recuperacao = calcular_notas_sigaa(
            FakeAluno(), avaliacoes_por_coluna, {"_modo": "recuperacao"}
        )
        assert recuperacao[Avaliacao.COLUNA_REC] == 8.0
        assert recuperacao["Resultado"] == 6.5  # (5+8)/2
        assert recuperacao["em_recuperacao"] is True
    finally:
        mod.media_ponderada_coluna = original
