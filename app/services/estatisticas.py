"""Cálculo de estatísticas de frequência e notas."""
from dataclasses import dataclass, field

from app.models import AlunoDisciplina, Avaliacao, Disciplina, Nota, Presenca
from app.services.academico import calcular_media_aluno, contar_faltas_aluno


LIMITE_FREQUENCIA = 75.0


@dataclass
class StatsAlunoFrequencia:
    aluno: AlunoDisciplina
    presencas: int
    faltas: int
    justificadas: int
    nao_registradas: int
    frequencia_pct: float | None
    frequencia_com_justificativa_pct: float | None
    abaixo_limite: bool


@dataclass
class StatsAlunoNota:
    aluno: AlunoDisciplina
    media: float | None
    notas_por_avaliacao: dict[int, float | None]
    acima_media_turma: bool | None


@dataclass
class StatsAvaliacao:
    avaliacao: Avaliacao
    media: float | None
    minima: float | None
    maxima: float | None
    quantidade: int


@dataclass
class EstatisticasDisciplina:
    total_alunos: int
    total_aulas: int
    total_chamadas: int
    total_avaliacoes: int

    # Frequência — turma
    freq_media_turma: float | None
    freq_com_just_media_turma: float | None
    alunos_abaixo_limite: int
    total_presencas: int
    total_faltas: int
    total_justificadas: int

    # Notas — turma
    media_geral_turma: float | None
    distribuicao_notas: dict[str, int]
    avaliacoes_stats: list[StatsAvaliacao]

    # Por aluno
    alunos_frequencia: list[StatsAlunoFrequencia] = field(default_factory=list)
    alunos_notas: list[StatsAlunoNota] = field(default_factory=list)


def _aulas_com_chamada(disciplina: Disciplina) -> int:
    return sum(1 for aula in disciplina.aulas.all() if aula.presencas.count() > 0)


def _stats_frequencia_aluno(aluno: AlunoDisciplina, total_chamadas: int) -> StatsAlunoFrequencia:
    presencas = aluno.presencas.filter_by(status=Presenca.STATUS_PRESENTE).count()
    faltas = aluno.presencas.filter_by(status=Presenca.STATUS_AUSENTE).count()
    justificadas = aluno.presencas.filter_by(status=Presenca.STATUS_JUSTIFICADO).count()
    registradas = presencas + faltas + justificadas
    nao_registradas = max(total_chamadas - registradas, 0)

    freq = round(presencas / total_chamadas * 100, 1) if total_chamadas > 0 else None
    freq_j = (
        round((presencas + justificadas) / total_chamadas * 100, 1) if total_chamadas > 0 else None
    )

    return StatsAlunoFrequencia(
        aluno=aluno,
        presencas=presencas,
        faltas=faltas,
        justificadas=justificadas,
        nao_registradas=nao_registradas,
        frequencia_pct=freq,
        frequencia_com_justificativa_pct=freq_j,
        abaixo_limite=freq is not None and freq < LIMITE_FREQUENCIA,
    )


def _stats_avaliacao(avaliacao: Avaliacao) -> StatsAvaliacao:
    valores = [n.valor for n in avaliacao.notas.all() if n.valor is not None]
    if not valores:
        return StatsAvaliacao(avaliacao=avaliacao, media=None, minima=None, maxima=None, quantidade=0)
    return StatsAvaliacao(
        avaliacao=avaliacao,
        media=round(sum(valores) / len(valores), 2),
        minima=min(valores),
        maxima=max(valores),
        quantidade=len(valores),
    )


def _distribuicao_notas(medias: list[float]) -> dict[str, int]:
    faixas = {"0 — 4,9": 0, "5,0 — 6,9": 0, "7,0 — 8,9": 0, "9,0 — 10": 0}
    for m in medias:
        if m < 5:
            faixas["0 — 4,9"] += 1
        elif m < 7:
            faixas["5,0 — 6,9"] += 1
        elif m < 9:
            faixas["7,0 — 8,9"] += 1
        else:
            faixas["9,0 — 10"] += 1
    return faixas


def calcular_estatisticas(disciplina: Disciplina) -> EstatisticasDisciplina:
    alunos = disciplina.alunos.order_by(AlunoDisciplina.nome).all()
    avaliacoes = disciplina.avaliacoes.order_by(Avaliacao.ordem).all()
    total_aulas = disciplina.aulas.count()
    total_chamadas = _aulas_com_chamada(disciplina)

    alunos_freq = [_stats_frequencia_aluno(a, total_chamadas) for a in alunos]

    freqs = [a.frequencia_pct for a in alunos_freq if a.frequencia_pct is not None]
    freqs_j = [a.frequencia_com_justificativa_pct for a in alunos_freq if a.frequencia_com_justificativa_pct is not None]

    avaliacoes_stats = [_stats_avaliacao(av) for av in avaliacoes]

    medias_alunos: list[tuple[AlunoDisciplina, float | None]] = [
        (a, calcular_media_aluno(a, disciplina.id)) for a in alunos
    ]
    medias_validas = [m for _, m in medias_alunos if m is not None]
    media_turma = round(sum(medias_validas) / len(medias_validas), 2) if medias_validas else None

    notas_por_aluno_map: dict[int, dict[int, float | None]] = {}
    for nota in Nota.query.join(Avaliacao).filter(Avaliacao.disciplina_id == disciplina.id).all():
        notas_por_aluno_map.setdefault(nota.aluno_disciplina_id, {})[nota.avaliacao_id] = nota.valor

    alunos_notas = []
    for aluno, media in medias_alunos:
        acima = None
        if media is not None and media_turma is not None:
            acima = media >= media_turma
        alunos_notas.append(
            StatsAlunoNota(
                aluno=aluno,
                media=media,
                notas_por_avaliacao={
                    av.id: notas_por_aluno_map.get(aluno.id, {}).get(av.id) for av in avaliacoes
                },
                acima_media_turma=acima,
            )
        )

    alunos_notas.sort(key=lambda x: (x.media is None, -(x.media or 0)))

    return EstatisticasDisciplina(
        total_alunos=len(alunos),
        total_aulas=total_aulas,
        total_chamadas=total_chamadas,
        total_avaliacoes=len(avaliacoes),
        freq_media_turma=round(sum(freqs) / len(freqs), 1) if freqs else None,
        freq_com_just_media_turma=round(sum(freqs_j) / len(freqs_j), 1) if freqs_j else None,
        alunos_abaixo_limite=sum(1 for a in alunos_freq if a.abaixo_limite),
        total_presencas=sum(a.presencas for a in alunos_freq),
        total_faltas=sum(a.faltas for a in alunos_freq),
        total_justificadas=sum(a.justificadas for a in alunos_freq),
        media_geral_turma=media_turma,
        distribuicao_notas=_distribuicao_notas(medias_validas),
        avaliacoes_stats=avaliacoes_stats,
        alunos_frequencia=alunos_freq,
        alunos_notas=alunos_notas,
    )
