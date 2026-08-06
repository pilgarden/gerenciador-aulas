"""Grupos de alunos e lançamento de notas em grupo."""
from app.extensions import db
from app.models import AlunoDisciplina, Avaliacao, Disciplina, Grupo, GrupoMembro, Nota, Semestre, Usuario
from app.services.grupos import copiar_padrao_para_avaliacao, garantir_grupos_avaliacao, salvar_divisao_grupos


def _setup_turma(app):
    admin = Usuario.query.filter_by(email="admin@test.com").first()
    semestre = Semestre(codigo="2026.2", ativo=True)
    db.session.add(semestre)
    db.session.flush()
    disc = Disciplina(
        usuario_id=admin.id,
        semestre_id=semestre.id,
        codigo="GRP1",
        nome="Turma Grupos",
        turma="01",
    )
    db.session.add(disc)
    db.session.flush()
    a1 = AlunoDisciplina(disciplina_id=disc.id, matricula="1", nome="Alice")
    a2 = AlunoDisciplina(disciplina_id=disc.id, matricula="2", nome="Bob")
    a3 = AlunoDisciplina(disciplina_id=disc.id, matricula="3", nome="Carol")
    db.session.add_all([a1, a2, a3])
    db.session.flush()
    return disc, a1, a2, a3


def test_copia_padrao_para_avaliacao(app):
    with app.app_context():
        disc, a1, a2, a3 = _setup_turma(app)
        salvar_divisao_grupos(
            disc.id,
            None,
            ["Grupo Alpha", "Grupo Beta"],
            [[a1.id, a2.id], [a3.id]],
        )
        av = Avaliacao(
            disciplina_id=disc.id,
            nome="Trabalho 1",
            peso=1.0,
            ordem=0,
            em_grupo=True,
            coluna_sigaa=Avaliacao.COLUNA_UNID1,
        )
        db.session.add(av)
        db.session.commit()

        grupos = garantir_grupos_avaliacao(disc.id, av)
        assert len(grupos) == 2
        assert {g.nome for g in grupos} == {"Grupo Alpha", "Grupo Beta"}
        membros_alpha = {m.aluno_disciplina_id for g in grupos if g.nome == "Grupo Alpha" for m in g.membros}
        assert membros_alpha == {a1.id, a2.id}


def test_lancamento_nota_grupo_replica(logged_client, app):
    with app.app_context():
        disc, a1, a2, a3 = _setup_turma(app)
        av = Avaliacao(
            disciplina_id=disc.id,
            nome="Trabalho",
            peso=1.0,
            ordem=0,
            em_grupo=True,
            coluna_sigaa=Avaliacao.COLUNA_UNID1,
        )
        db.session.add(av)
        db.session.flush()
        g = Grupo(disciplina_id=disc.id, avaliacao_id=av.id, nome="G1", ordem=0)
        db.session.add(g)
        db.session.flush()
        db.session.add_all(
            [
                GrupoMembro(grupo_id=g.id, aluno_disciplina_id=a1.id),
                GrupoMembro(grupo_id=g.id, aluno_disciplina_id=a2.id),
            ]
        )
        db.session.commit()
        disc_id, av_id, g_id = disc.id, av.id, g.id
        a1_id, a2_id, a3_id = a1.id, a2.id, a3.id

    resp = logged_client.post(
        f"/disciplinas/{disc_id}/notas/",
        data={
            f"nota_grupo_{g_id}_{av_id}": "8,5",
            f"nota_{a3_id}_{av_id}": "7",
        },
        follow_redirects=True,
    )
    assert resp.status_code == 200

    with app.app_context():
        n1 = Nota.query.filter_by(avaliacao_id=av_id, aluno_disciplina_id=a1_id).first()
        n2 = Nota.query.filter_by(avaliacao_id=av_id, aluno_disciplina_id=a2_id).first()
        n3 = Nota.query.filter_by(avaliacao_id=av_id, aluno_disciplina_id=a3_id).first()
        assert n1 is not None and abs(n1.valor - 8.5) < 0.01
        assert n2 is not None and abs(n2.valor - 8.5) < 0.01
        assert n3 is not None and abs(n3.valor - 7.0) < 0.01


def test_recarregar_padrao(app):
    with app.app_context():
        disc, a1, a2, a3 = _setup_turma(app)
        salvar_divisao_grupos(disc.id, None, ["Padrão"], [[a1.id, a2.id, a3.id]])
        av = Avaliacao(
            disciplina_id=disc.id,
            nome="Lista",
            peso=1.0,
            ordem=0,
            em_grupo=True,
            coluna_sigaa=Avaliacao.COLUNA_UNID2,
        )
        db.session.add(av)
        db.session.commit()
        garantir_grupos_avaliacao(disc.id, av)
        # altera avaliação
        salvar_divisao_grupos(disc.id, av.id, ["Só Alice"], [[a1.id]])
        assert len(Grupo.query.filter_by(avaliacao_id=av.id).all()) == 1
        # recarrega
        copiar_padrao_para_avaliacao(disc.id, av)
        grupos = Grupo.query.filter_by(avaliacao_id=av.id).all()
        assert len(grupos) == 1
        assert grupos[0].nome == "Padrão"
        assert {m.aluno_disciplina_id for m in grupos[0].membros} == {a1.id, a2.id, a3.id}
