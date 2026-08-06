"""Testes de relatório PDF para alunos."""
from app.extensions import db
from app.models import AlunoDisciplina, Avaliacao, Disciplina, Nota, Semestre, Usuario
from app.services.relatorio_pdf import (
    RelatorioConfig,
    gerar_pdf_relatorio,
    mascarar_matricula,
)


def test_mascarar_matricula():
    assert mascarar_matricula("20222006643", "completa", 4) == "20222006643"
    assert mascarar_matricula("20222006643", "parcial", 4) == "*******6643"
    assert mascarar_matricula("123", "parcial", 4) == "123"


def test_gerar_pdf_notas_unir(app, disciplina_com_alunos):
    with app.app_context():
        admin = Usuario.query.filter_by(email="admin@test.com").first()
        admin.acesso_cabecalho_unir = True
        admin.tratamento = "Prof. Dr."
        av = Avaliacao(
            disciplina_id=disciplina_com_alunos.id,
            nome="Prova 1",
            peso=1.0,
            ordem=0,
            coluna_sigaa=Avaliacao.COLUNA_UNID1,
        )
        db.session.add(av)
        db.session.flush()
        aluno = disciplina_com_alunos.alunos.first()
        db.session.add(Nota(avaliacao_id=av.id, aluno_disciplina_id=aluno.id, valor=8.5))
        db.session.commit()

        pdf = gerar_pdf_relatorio(
            disciplina_com_alunos,
            admin,
            RelatorioConfig(
                tipo="notas",
                matricula_modo="parcial",
                digitos_matricula=4,
                incluir_nome=True,
                incluir_media=True,
                usar_cabecalho_unir=True,
            ),
        )
        assert pdf[:4] == b"%PDF"
        assert len(pdf) > 500


def test_rota_relatorio_pdf(logged_client, disciplina_com_alunos, app):
    with app.app_context():
        admin = Usuario.query.filter_by(email="admin@test.com").first()
        admin.acesso_cabecalho_unir = True
        db.session.commit()
        disc_id = disciplina_com_alunos.id

    resp = logged_client.post(
        f"/disciplinas/{disc_id}/relatorios/",
        data={
            "tipo": "faltas",
            "matricula_modo": "parcial",
            "digitos_matricula": "4",
            "incluir_nome": "y",
            "cabecalho": "unir",
            "titulo_custom": "Faltas da turma",
        },
    )
    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data[:4] == b"%PDF"
