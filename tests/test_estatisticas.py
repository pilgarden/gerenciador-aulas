"""Testes de estatísticas."""
from datetime import date

from app.extensions import db
from app.models import AlunoDisciplina, Aula, Avaliacao, Nota, Presenca
from app.services.estatisticas import LIMITE_FREQUENCIA, calcular_estatisticas


def test_estatisticas_frequencia(disciplina_com_alunos, app):
    with app.app_context():
        d = disciplina_com_alunos
        aula = Aula(disciplina_id=d.id, data=date(2026, 7, 28), numero=1)
        db.session.add(aula)
        db.session.flush()

        alunos = AlunoDisciplina.query.filter_by(disciplina_id=d.id).all()
        db.session.add(
            Presenca(aula_id=aula.id, aluno_disciplina_id=alunos[0].id, status=Presenca.STATUS_PRESENTE)
        )
        db.session.add(
            Presenca(aula_id=aula.id, aluno_disciplina_id=alunos[1].id, status=Presenca.STATUS_AUSENTE)
        )
        db.session.commit()

        stats = calcular_estatisticas(d)
        assert stats.total_chamadas == 1
        assert stats.freq_media_turma == 50.0
        assert stats.alunos_abaixo_limite == 1
        assert stats.total_presencas == 1
        assert stats.total_faltas == 1


def test_estatisticas_notas(disciplina_com_alunos, app):
    with app.app_context():
        d = disciplina_com_alunos
        av = Avaliacao(disciplina_id=d.id, nome="Unid. 1", peso=1.0, ordem=0)
        db.session.add(av)
        db.session.flush()

        alunos = AlunoDisciplina.query.filter_by(disciplina_id=d.id).all()
        db.session.add(Nota(avaliacao_id=av.id, aluno_disciplina_id=alunos[0].id, valor=8.0))
        db.session.add(Nota(avaliacao_id=av.id, aluno_disciplina_id=alunos[1].id, valor=6.0))
        db.session.commit()

        stats = calcular_estatisticas(d)
        assert stats.media_geral_turma == 7.0
        assert stats.avaliacoes_stats[0].media == 7.0
        assert stats.avaliacoes_stats[0].minima == 6.0
        assert stats.avaliacoes_stats[0].maxima == 8.0
        assert sum(stats.distribuicao_notas.values()) == 2


def test_rota_estatisticas(logged_client, disciplina_com_alunos):
    resp = logged_client.get(f"/disciplinas/{disciplina_com_alunos.id}/estatisticas/")
    assert resp.status_code == 200
    assert b"Estat" in resp.data
