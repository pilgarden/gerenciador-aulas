"""Helpers para mapear avaliações às colunas fixas do SIGAA."""
from app.models import Avaliacao


def detectar_coluna_sigaa(nome: str) -> str:
    """Infere a coluna SIGAA a partir do nome da avaliação/coluna importada."""
    texto = (nome or "").strip().lower()
    texto_norm = (
        texto.replace("unidade", "unid")
        .replace("recuperaçao", "rec")
        .replace("recuperacao", "rec")
        .replace("recuperação", "rec")
    )

    if texto_norm in ("rec.", "rec", "recuperação", "recuperacao"):
        return Avaliacao.COLUNA_REC
    if "rec" == texto_norm or texto_norm.startswith("rec.") or texto_norm.startswith("rec "):
        return Avaliacao.COLUNA_REC

    if "2" in texto_norm and ("unid" in texto_norm or "u2" in texto_norm or texto_norm in ("2",)):
        return Avaliacao.COLUNA_UNID2
    if texto_norm in ("unid. 2", "unid 2", "unid.2", "u2"):
        return Avaliacao.COLUNA_UNID2

    if "1" in texto_norm and ("unid" in texto_norm or "u1" in texto_norm):
        return Avaliacao.COLUNA_UNID1
    if texto_norm in ("unid. 1", "unid 1", "unid.1", "u1"):
        return Avaliacao.COLUNA_UNID1

    # Padrão: Unid. 1
    return Avaliacao.COLUNA_UNID1
