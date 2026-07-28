"""Testes da exportação SIGAA no formato fixo."""
import xlrd

from app.extensions import db
from app.models import AlunoDisciplina, Avaliacao, Disciplina, Nota, Semestre
from app.services.sigaa_export import gerar_planilha_sigaa, nome_arquivo_exportacao


def test_gerar_planilha_formato_fixo_sigaa(app):
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

        # Avaliações internas variadas, mapeadas às colunas SIGAA
        p1 = Avaliacao(
            disciplina_id=disciplina.id,
            nome="Prova 1",
            peso=2.0,
            ordem=0,
            coluna_sigaa=Avaliacao.COLUNA_UNID1,
        )
        t1 = Avaliacao(
            disciplina_id=disciplina.id,
            nome="Trabalho 1",
            peso=1.0,
            ordem=1,
            coluna_sigaa=Avaliacao.COLUNA_UNID1,
        )
        p2 = Avaliacao(
            disciplina_id=disciplina.id,
            nome="Prova 2",
            peso=1.0,
            ordem=2,
            coluna_sigaa=Avaliacao.COLUNA_UNID2,
        )
        db.session.add_all([p1, t1, p2])
        db.session.flush()

        # Unid. 1 = (8*2 + 7*1) / 3 = 7.666... → 7.67
        db.session.add(Nota(avaliacao_id=p1.id, aluno_disciplina_id=aluno.id, valor=8.0))
        db.session.add(Nota(avaliacao_id=t1.id, aluno_disciplina_id=aluno.id, valor=7.0))
        db.session.add(Nota(avaliacao_id=p2.id, aluno_disciplina_id=aluno.id, valor=9.0))
        db.session.commit()

        conteudo = gerar_planilha_sigaa(disciplina)
        book = xlrd.open_workbook(file_contents=conteudo)
        sheet = book.sheet_by_index(0)

        assert sheet.cell_value(1, 1) == "PLANILHA DE NOTAS"
        assert "DEC10058" in sheet.cell_value(2, 1)

        # Cabeçalho fixo
        assert sheet.cell_value(10, 1) == "Matrícula"
        assert sheet.cell_value(10, 2) == "Nome"
        assert sheet.cell_value(10, 3) == "Unid. 1"
        assert sheet.cell_value(10, 4) == "Unid. 2"
        assert sheet.cell_value(10, 5) == "Rec."
        assert sheet.cell_value(10, 6) == "Resultado"
        assert sheet.cell_value(10, 7) == "Faltas"
        assert sheet.cell_value(10, 8) == "Sit."

        assert sheet.cell_value(11, 1) == "20222006643"
        assert sheet.cell_value(11, 3) == "7,67"  # média ponderada Unid. 1
        assert sheet.cell_value(11, 4) == "9"  # Unid. 2
        assert sheet.cell_value(11, 5) == "-"  # Rec. vazia
        # Resultado = média de Unid.1 e Unid.2 = (7.67+9)/2 = 8.335 → 8.34
        assert abs(float(sheet.cell_value(11, 6)) - 8.34) < 0.01


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
        av = Avaliacao(
            disciplina_id=disciplina_com_alunos.id,
            nome="Prova 1",
            peso=1.0,
            ordem=0,
            coluna_sigaa=Avaliacao.COLUNA_UNID1,
        )
        db.session.add(av)
        db.session.commit()

    resp = logged_client.get(f"/disciplinas/{disciplina_com_alunos.id}/exportar")
    assert resp.status_code == 200
    assert "application/vnd.ms-excel" in resp.headers["Content-Type"]

    book = xlrd.open_workbook(file_contents=resp.data)
    sheet = book.sheet_by_index(0)
    assert sheet.cell_value(10, 3) == "Unid. 1"
    assert sheet.cell_value(10, 4) == "Unid. 2"
    assert sheet.cell_value(10, 5) == "Rec."
