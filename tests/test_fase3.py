"""Testes da Fase 3 — presença e notas."""
from datetime import date

from app.extensions import db
from app.models import (
    AlunoDisciplina,
    Aula,
    Avaliacao,
    Nota,
    Presenca,
)


def test_criar_aula_e_chamada(logged_client, disciplina_com_alunos):
    d = disciplina_com_alunos
    resp = logged_client.post(
        f"/disciplinas/{d.id}/aulas/nova",
        data={"data": "2026-07-28", "numero": "1", "conteudo": "Aula introdutória"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    aula = Aula.query.filter_by(disciplina_id=d.id).first()
    assert aula is not None
    assert aula.conteudo == "Aula introdutória"

    alunos = AlunoDisciplina.query.filter_by(disciplina_id=d.id).all()
    resp = logged_client.post(
        f"/disciplinas/{d.id}/aulas/{aula.id}/chamada",
        data={
            f"presenca_{alunos[0].id}": Presenca.STATUS_PRESENTE,
            f"presenca_{alunos[1].id}": Presenca.STATUS_AUSENTE,
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert Presenca.query.filter_by(status=Presenca.STATUS_AUSENTE).count() == 1


def test_resumo_faltas(logged_client, disciplina_com_alunos):
    d = disciplina_com_alunos
    aula = Aula(disciplina_id=d.id, data=date(2026, 7, 28), numero=1)
    db.session.add(aula)
    db.session.flush()
    aluno = AlunoDisciplina.query.filter_by(disciplina_id=d.id).first()
    db.session.add(
        Presenca(
            aula_id=aula.id,
            aluno_disciplina_id=aluno.id,
            status=Presenca.STATUS_AUSENTE,
        )
    )
    db.session.commit()

    resp = logged_client.get(f"/disciplinas/{d.id}/aulas/resumo")
    assert resp.status_code == 200
    assert b"Resumo de faltas" in resp.data


def test_lancamento_notas(logged_client, disciplina_com_alunos):
    d = disciplina_com_alunos
    av1 = Avaliacao(disciplina_id=d.id, nome="Unid. 1", peso=1.0, ordem=0)
    av2 = Avaliacao(disciplina_id=d.id, nome="Unid. 2", peso=1.0, ordem=1)
    db.session.add_all([av1, av2])
    db.session.commit()

    alunos = AlunoDisciplina.query.filter_by(disciplina_id=d.id).all()
    resp = logged_client.post(
        f"/disciplinas/{d.id}/notas/",
        data={
            f"nota_{alunos[0].id}_{av1.id}": "8.5",
            f"nota_{alunos[0].id}_{av2.id}": "7.0",
            f"nota_{alunos[1].id}_{av1.id}": "9.0",
            f"nota_{alunos[1].id}_{av2.id}": "6.5",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert Nota.query.count() == 4

    nota = Nota.query.filter_by(aluno_disciplina_id=alunos[0].id, avaliacao_id=av1.id).first()
    assert nota.valor == 8.5


def test_criar_avaliacao(logged_client, disciplina_com_alunos):
    d = disciplina_com_alunos
    resp = logged_client.post(
        f"/disciplinas/{d.id}/notas/avaliacoes/nova",
        data={"nome": "Prova Final", "peso": "2", "ordem": "0"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert Avaliacao.query.filter_by(nome="Prova Final").first() is not None
