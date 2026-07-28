import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import create_app
from app.extensions import db
from app.models import AlunoDisciplina, Disciplina, Semestre, Usuario


@pytest.fixture
def app():
    app = create_app("development")
    app.config.update(
        TESTING=True,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        WTF_CSRF_ENABLED=False,
        SECRET_KEY="test",
    )
    with app.app_context():
        db.create_all()
        admin = Usuario(nome="Admin", email="admin@test.com", papel=Usuario.PAPEL_ADMIN, ativo=True)
        admin.set_senha("senha1234")
        db.session.add(admin)
        db.session.commit()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def logged_client(client):
    client.post("/login", data={"email": "admin@test.com", "senha": "senha1234"})
    return client


@pytest.fixture
def disciplina_com_alunos(app):
    semestre = Semestre(codigo="2026.2", ativo=True)
    db.session.add(semestre)
    db.session.flush()
    disciplina = Disciplina(
        semestre_id=semestre.id, codigo="DEC10058", nome="Teste", turma="01", carga_horaria=60
    )
    db.session.add(disciplina)
    db.session.flush()
    aluno1 = AlunoDisciplina(disciplina_id=disciplina.id, matricula="111", nome="Aluno A")
    aluno2 = AlunoDisciplina(disciplina_id=disciplina.id, matricula="222", nome="Aluno B")
    db.session.add_all([aluno1, aluno2])
    db.session.commit()
    return disciplina
