"""Testes da Fase 2 com app Flask."""
import io

import pytest

from app.extensions import db
from app.models import AlunoDisciplina, Disciplina, Semestre


def test_criar_semestre_e_disciplina(logged_client):
    resp = logged_client.post("/semestres/novo", data={"codigo": "2026.2", "ativo": "y"}, follow_redirects=True)
    assert resp.status_code == 200
    assert Semestre.query.filter_by(codigo="2026.2").first() is not None

    semestre = Semestre.query.first()
    resp = logged_client.post(
        "/disciplinas/novo",
        data={
            "semestre_id": semestre.id,
            "codigo": "DEC10058",
            "nome": "Elementos Finitos",
            "turma": "01",
            "carga_horaria": "60",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert Disciplina.query.filter_by(codigo="DEC10058").first() is not None


def test_criar_aluno_manual(logged_client):
    semestre = Semestre(codigo="2026.2", ativo=True)
    db.session.add(semestre)
    db.session.flush()
    disciplina = Disciplina(
        semestre_id=semestre.id, codigo="DEC10058", nome="Teste", turma="01"
    )
    db.session.add(disciplina)
    db.session.commit()

    resp = logged_client.post(
        f"/disciplinas/{disciplina.id}/alunos/novo",
        data={"matricula": "20222006643", "nome": "Aluno Teste", "faltas_sigaa": "0"},
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert AlunoDisciplina.query.filter_by(matricula="20222006643").first() is not None


def test_importar_sigaa(logged_client, app):
    from pathlib import Path

    sample = Path(r"c:\Users\Pedro\Downloads\notas_DEC10058_T01_20262.xls.xls")
    if not sample.exists():
        pytest.skip("Planilha SIGAA de exemplo não encontrada")

    with app.app_context():
        data = {"arquivo": (io.BytesIO(sample.read_bytes()), "notas.xls")}
        resp = logged_client.post(
            "/disciplinas/importar",
            data=data,
            content_type="multipart/form-data",
            follow_redirects=True,
        )
        assert resp.status_code == 200
        assert b"Confirmar import" in resp.data or "Confirmar import".encode() in resp.data

        resp = logged_client.post("/disciplinas/importar/confirmar", follow_redirects=True)
        assert resp.status_code == 200
        assert Disciplina.query.filter_by(codigo="DEC10058").first() is not None
        assert AlunoDisciplina.query.count() >= 1
