"""Aplica resultado da importação SIGAA ao banco de dados."""
from app.extensions import db
from app.models import AlunoDisciplina, Avaliacao, Disciplina, Nota, Semestre, Usuario
from app.services.sigaa_colunas import detectar_coluna_sigaa
from app.services.sigaa_import import SigaaImportResult


def _get_or_create_semestre(codigo: str) -> Semestre:
    semestre = Semestre.query.filter_by(codigo=codigo).first()
    if semestre:
        return semestre
    semestre = Semestre(codigo=codigo, ativo=Semestre.query.count() == 0)
    db.session.add(semestre)
    db.session.flush()
    return semestre


def _sync_avaliacoes(disciplina: Disciplina, colunas: list[str]) -> dict[str, Avaliacao]:
    avaliacoes: dict[str, Avaliacao] = {}
    for ordem, nome in enumerate(colunas):
        coluna_sigaa = detectar_coluna_sigaa(nome)
        avaliacao = Avaliacao.query.filter_by(disciplina_id=disciplina.id, nome=nome).first()
        if not avaliacao:
            avaliacao = Avaliacao(
                disciplina_id=disciplina.id,
                nome=nome,
                ordem=ordem,
                coluna_sigaa=coluna_sigaa,
            )
            db.session.add(avaliacao)
            db.session.flush()
        else:
            avaliacao.ordem = ordem
            if not avaliacao.coluna_sigaa:
                avaliacao.coluna_sigaa = coluna_sigaa
            elif nome.strip().lower() in (
                "unid. 1",
                "unid. 2",
                "rec.",
                "unid 1",
                "unid 2",
                "rec",
            ):
                avaliacao.coluna_sigaa = coluna_sigaa
        avaliacoes[nome] = avaliacao
    return avaliacoes


def aplicar_importacao_sigaa(
    result: SigaaImportResult,
    disciplina_id: int | None = None,
    usuario_id: int | None = None,
) -> tuple[Disciplina, dict[str, int]]:
    semestre = _get_or_create_semestre(result.semestre)
    usuario = db.session.get(Usuario, usuario_id) if usuario_id else None

    if disciplina_id:
        disciplina = db.session.get(Disciplina, disciplina_id)
        if disciplina is None:
            raise ValueError("Disciplina não encontrada.")
        if usuario is not None and not disciplina.tem_acesso(usuario):
            raise ValueError("Sem permissão para importar nesta disciplina.")
    else:
        if usuario_id is None:
            raise ValueError("usuario_id é obrigatório para criar disciplina na importação.")
        disciplina = Disciplina.query.filter_by(
            semestre_id=semestre.id,
            codigo=result.codigo,
            turma=result.turma,
        ).first()
        if disciplina:
            if usuario is not None and not disciplina.tem_acesso(usuario):
                raise ValueError(
                    f"A disciplina {result.codigo} turma {result.turma} já existe e pertence "
                    f"a outro professor. Peça ao administrador para compartilhá-la."
                )
            disciplina.nome = result.nome
            disciplina.carga_horaria = result.carga_horaria
        else:
            disciplina = Disciplina(
                usuario_id=usuario_id,
                semestre_id=semestre.id,
                codigo=result.codigo,
                nome=result.nome,
                turma=result.turma,
                carga_horaria=result.carga_horaria,
            )
            db.session.add(disciplina)
            db.session.flush()

    avaliacoes = _sync_avaliacoes(disciplina, result.colunas_notas)

    stats = {"criados": 0, "atualizados": 0}
    for aluno_data in result.alunos:
        aluno = AlunoDisciplina.query.filter_by(
            disciplina_id=disciplina.id,
            matricula=aluno_data.matricula,
        ).first()
        if aluno:
            aluno.nome = aluno_data.nome
            aluno.faltas_sigaa = aluno_data.faltas
            aluno.situacao = aluno_data.situacao
            stats["atualizados"] += 1
        else:
            aluno = AlunoDisciplina(
                disciplina_id=disciplina.id,
                matricula=aluno_data.matricula,
                nome=aluno_data.nome,
                faltas_sigaa=aluno_data.faltas,
                situacao=aluno_data.situacao,
            )
            db.session.add(aluno)
            db.session.flush()
            stats["criados"] += 1

        for nome_avaliacao, valor in aluno_data.notas.items():
            if valor is None or nome_avaliacao not in avaliacoes:
                continue
            avaliacao = avaliacoes[nome_avaliacao]
            nota = Nota.query.filter_by(
                avaliacao_id=avaliacao.id,
                aluno_disciplina_id=aluno.id,
            ).first()
            if nota:
                nota.valor = float(valor) if isinstance(valor, (int, float)) else None
            else:
                nota = Nota(
                    avaliacao_id=avaliacao.id,
                    aluno_disciplina_id=aluno.id,
                    valor=float(valor) if isinstance(valor, (int, float)) else None,
                )
                db.session.add(nota)

    db.session.commit()
    return disciplina, stats
