"""Testes da exportação SIGAA."""
import xlrd

from app.extensions import db
from app.models import AlunoDisciplina, Avaliacao, Disciplina, Nota, Semestre
from app.services.sigaa_export import gerar_planilha_sigaa, nome_arquivo_exportacao


def test_gerar_planilha_sigaa(app):
    with app.app_context():
        semestre = Semestre(codigo="2026.2", ativo=True)
        db.session.add(semestre)
        db.session.flush()
        disciplina = Disciplina(
            semestre_id=semestre.id,
            codigo="DEC10058",
            nome="Introdução ao MEF",
            turma="01",
            carga_horaria=60,
        )
        db.session.add(disciplina)
        db.session.flush()

        aluno = AlunoDisciplina(
            disciplina_id=disciplina.id,
            matricula="20222006643",
            nome="Aluno Teste",
            faltas_sigaa=1,
        )
        db.session.add(aluno)
        db.session.flush()

        av = Avaliacao(disciplina_id=disciplina.id, nome="Unid. 1", peso=1.0, ordem=0)
        db.session.add(av)
        db.session.flush()
        db.session.add(Nota(avaliacao_id=av.id, aluno_disciplina_id=aluno.id, valor=8.5))
        db.session.commit()

        conteudo = gerar_planilha_sigaa(disciplina)
        book = xlrd.open_workbook(file_contents=conteudo)
        sheet = book.sheet_by_index(0)
        assert sheet.cell_value(1, 1) == "PLANILHA DE NOTAS"
        assert "DEC10058" in sheet.cell_value(2, 1)
        assert sheet.cell_value(10, 1) == "Matrícula"
        assert sheet.cell_value(11, 1) == "20222006643"
        assert sheet.cell_value(11, 3) == "8,5"


def test_nome_arquivo_exportacao(app):
    with app.app_context():
        semestre = Semestre(codigo="2026.2", ativo=True)
        db.session.add(semestre)
        db.session.flush()
        disciplina = Disciplina(
            semestre_id=semestre.id,
            codigo="DEC10058",
            nome="Teste",
            turma="01",
        )
        db.session.add(disciplina)
        db.session.commit()
        assert nome_arquivo_exportacao(disciplina) == "notas_DEC10058_T01_20262.xls"


def test_rota_exportar(logged_client, disciplina_com_alunos, app):
    with app.app_context():
        av = Avaliacao(disciplina_id=disciplina_com_alunos.id, nome="Unid. 1", peso=1.0, ordem=0)
        db.session.add(av)
        db.session.commit()

    resp = logged_client.get(f"/disciplinas/{disciplina_com_alunos.id}/exportar")
    assert resp.status_code == 200
    assert "application/vnd.ms-excel" in resp.headers["Content-Type"]
    assert len(resp.data) > 100

    book = xlrd.open_workbook(file_contents=resp.data)
    assert book.sheet_by_index(0).cell_value(1, 1) == "PLANILHA DE NOTAS"
