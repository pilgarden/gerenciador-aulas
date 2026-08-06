"""Isolamento de disciplinas entre professores."""
from app.extensions import db
from app.models import Disciplina, Semestre, Usuario


def _criar_professor(email: str, nome: str) -> Usuario:
    prof = Usuario(nome=nome, email=email, papel=Usuario.PAPEL_PROFESSOR, ativo=True)
    prof.set_senha("senha1234")
    db.session.add(prof)
    db.session.flush()
    return prof


def test_professor_nao_ve_disciplina_de_outro(client, app):
    with app.app_context():
        semestre = Semestre(codigo="2026.2", ativo=True)
        db.session.add(semestre)
        db.session.flush()

        prof_a = _criar_professor("prof.a@test.com", "Prof A")
        prof_b = _criar_professor("prof.b@test.com", "Prof B")

        disc_a = Disciplina(
            usuario_id=prof_a.id,
            semestre_id=semestre.id,
            codigo="DEC1",
            nome="Turma A",
            turma="01",
        )
        disc_b = Disciplina(
            usuario_id=prof_b.id,
            semestre_id=semestre.id,
            codigo="DEC2",
            nome="Turma B",
            turma="01",
        )
        db.session.add_all([disc_a, disc_b])
        db.session.commit()
        id_a, id_b = disc_a.id, disc_b.id

    client.post("/login", data={"email": "prof.a@test.com", "senha": "senha1234"})

    resp = client.get("/disciplinas/")
    assert resp.status_code == 200
    assert b"Turma A" in resp.data
    assert b"Turma B" not in resp.data

    resp = client.get(f"/disciplinas/{id_b}")
    assert resp.status_code == 302 or b"sem permiss" in resp.data.lower() or b"n\xc3\xa3o encontrada" in resp.data.lower()

    # Após redirect, deve bloquear acesso direto a notas/presenças
    resp = client.get(f"/disciplinas/{id_b}/notas/", follow_redirects=True)
    assert b"Turma B" not in resp.data or b"sem permiss" in resp.data.lower() or b"n\xc3\xa3o encontrada" in resp.data.lower()

    resp = client.get(f"/disciplinas/{id_a}")
    assert resp.status_code == 200
    assert b"Turma A" in resp.data


def test_admin_ve_outras_separado(logged_client, app):
    with app.app_context():
        semestre = Semestre(codigo="2026.2", ativo=True)
        db.session.add(semestre)
        db.session.flush()
        admin = Usuario.query.filter_by(email="admin@test.com").first()
        prof = _criar_professor("prof.c@test.com", "Prof C")

        minha = Disciplina(
            usuario_id=admin.id,
            semestre_id=semestre.id,
            codigo="ADM1",
            nome="Minha Admin",
            turma="01",
        )
        outra = Disciplina(
            usuario_id=prof.id,
            semestre_id=semestre.id,
            codigo="OUT1",
            nome="De Outro",
            turma="01",
        )
        db.session.add_all([minha, outra])
        db.session.commit()
        outra_id = outra.id

    resp = logged_client.get("/disciplinas/")
    assert resp.status_code == 200
    assert b"Minha Admin" in resp.data
    assert b"De Outro" not in resp.data

    resp = logged_client.get("/disciplinas/outras")
    assert resp.status_code == 200
    assert b"De Outro" in resp.data
    assert b"Minha Admin" not in resp.data

    # Admin ainda pode abrir a turma de outro
    resp = logged_client.get(f"/disciplinas/{outra_id}")
    assert resp.status_code == 200
    assert b"De Outro" in resp.data
