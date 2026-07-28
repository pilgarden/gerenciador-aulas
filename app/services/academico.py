"""Utilitários para presenças e notas."""
from app.models import AlunoDisciplina, Avaliacao, Nota, Presenca


def contar_faltas_aluno(aluno: AlunoDisciplina) -> int:
    return aluno.presencas.filter_by(status=Presenca.STATUS_AUSENTE).count()


def calcular_media_aluno(aluno: AlunoDisciplina, disciplina_id: int) -> float | None:
    """Média ponderada das avaliações de unidade (exclui Rec.)."""
    avaliacoes = (
        Avaliacao.query.filter_by(disciplina_id=disciplina_id)
        .filter(Avaliacao.coluna_sigaa != Avaliacao.COLUNA_REC)
        .order_by(Avaliacao.ordem)
        .all()
    )
    if not avaliacoes:
        return None

    total_peso = 0.0
    total_pontos = 0.0
    tem_nota = False

    for avaliacao in avaliacoes:
        nota = Nota.query.filter_by(
            avaliacao_id=avaliacao.id,
            aluno_disciplina_id=aluno.id,
        ).first()
        if nota and nota.valor is not None:
            tem_nota = True
            total_pontos += nota.valor * avaliacao.peso
            total_peso += avaliacao.peso

    if not tem_nota or total_peso == 0:
        return None
    return round(total_pontos / total_peso, 2)
