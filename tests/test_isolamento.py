"""Isolamento, compartilhamento e transferência de disciplinas."""
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
    assert resp.status_code == 302

    resp = client.get(f"/disciplinas/{id_a}")
    assert resp.status_code == 200
    assert b"Turma A" in resp.data


def test_colaborador_acessa_disciplina(client, app):
    with app.app_context():
        semestre = Semestre(codigo="2026.2", ativo=True)
        db.session.add(semestre)
        db.session.flush()
        dono = _criar_professor("dono@test.com", "Dono")
        collab = _criar_professor("collab@test.com", "Collab")
        disc = Disciplina(
            usuario_id=dono.id,
            semestre_id=semestre.id,
            codigo="SHR1",
            nome="Compartilhada",
            turma="01",
        )
        db.session.add(disc)
        db.session.flush()
        disc.colaboradores.append(collab)
        db.session.commit()
        disc_id = disc.id

    client.post("/login", data={"email": "collab@test.com", "senha": "senha1234"})
    resp = client.get("/disciplinas/")
    assert b"Compartilhada" in resp.data
    resp = client.get(f"/disciplinas/{disc_id}")
    assert resp.status_code == 200
    assert b"Compartilhada" in resp.data


def test_admin_transfere_dono(logged_client, app):
    with app.app_context():
        semestre = Semestre(codigo="2026.2", ativo=True)
        db.session.add(semestre)
        db.session.flush()
        admin = Usuario.query.filter_by(email="admin@test.com").first()
        raduan = _criar_professor("raduan@test.com", "Raduan")
        disc = Disciplina(
            usuario_id=admin.id,
            semestre_id=semestre.id,
            codigo="DAE00447",
            nome="Do Raduan",
            turma="01",
        )
        db.session.add(disc)
        db.session.commit()
        disc_id = disc.id
        raduan_id = raduan.id

    resp = logged_client.post(
        f"/disciplinas/{disc_id}/professores",
        data={
            "dono_id": raduan_id,
            "colaboradores": [],
            "manter_dono_anterior_como_colaborador": "y",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        disc = db.session.get(Disciplina, disc_id)
        assert disc.usuario_id == raduan_id
        assert any(c.email == "admin@test.com" for c in disc.colaboradores)


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

    resp = logged_client.get(f"/disciplinas/{outra_id}")
    assert resp.status_code == 200
    assert b"De Outro" in resp.data
