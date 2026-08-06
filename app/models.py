from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


disciplina_colaboradores = db.Table(
    "disciplina_colaboradores",
    db.Column("disciplina_id", db.Integer, db.ForeignKey("disciplinas.id"), primary_key=True),
    db.Column("usuario_id", db.Integer, db.ForeignKey("usuarios.id"), primary_key=True),
)


class Usuario(UserMixin, db.Model):
    __tablename__ = "usuarios"

    PAPEL_ADMIN = "admin"
    PAPEL_PROFESSOR = "professor"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(256), nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    papel = db.Column(db.String(20), nullable=False, default=PAPEL_PROFESSOR)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    # Acesso ao cabeçalho pré-formatado Engenharia Civil / UNIR nos PDFs
    acesso_cabecalho_unir = db.Column(db.Boolean, default=False, nullable=False)
    # Ex.: "Prof. Dr.", "Prof.", "Profa. Dra."
    tratamento = db.Column(db.String(40), nullable=False, default="Prof.")
    criado_em = db.Column(db.DateTime, default=utcnow, nullable=False)

    disciplinas = db.relationship("Disciplina", back_populates="professor", lazy="dynamic")
    disciplinas_colaborando = db.relationship(
        "Disciplina",
        secondary=disciplina_colaboradores,
        back_populates="colaboradores",
        lazy="dynamic",
    )

    def set_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def check_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

    @property
    def is_admin(self):
        return self.papel == self.PAPEL_ADMIN

    def __repr__(self):
        return f"<Usuario {self.email}>"


class Semestre(db.Model):
    __tablename__ = "semestres"

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(10), unique=True, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    disciplinas = db.relationship("Disciplina", back_populates="semestre", lazy="dynamic")

    def __repr__(self):
        return f"<Semestre {self.codigo}>"


class Disciplina(db.Model):
    __tablename__ = "disciplinas"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuarios.id"), nullable=False, index=True)
    semestre_id = db.Column(db.Integer, db.ForeignKey("semestres.id"), nullable=False)
    codigo = db.Column(db.String(20), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    turma = db.Column(db.String(10), nullable=False, default="01")
    carga_horaria = db.Column(db.Integer, nullable=True)
    aulas_previstas = db.Column(db.Integer, nullable=True)

    professor = db.relationship("Usuario", back_populates="disciplinas")
    colaboradores = db.relationship(
        "Usuario",
        secondary=disciplina_colaboradores,
        back_populates="disciplinas_colaborando",
        lazy="selectin",
    )
    semestre = db.relationship("Semestre", back_populates="disciplinas")
    alunos = db.relationship(
        "AlunoDisciplina", back_populates="disciplina", lazy="dynamic", cascade="all, delete-orphan"
    )
    aulas = db.relationship(
        "Aula", back_populates="disciplina", lazy="dynamic", cascade="all, delete-orphan"
    )
    avaliacoes = db.relationship(
        "Avaliacao", back_populates="disciplina", lazy="dynamic", cascade="all, delete-orphan"
    )
    grupos = db.relationship(
        "Grupo", back_populates="disciplina", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint(
            "semestre_id",
            "codigo",
            "turma",
            name="uq_disciplina_semestre_codigo_turma",
        ),
    )

    def tem_acesso(self, usuario: Usuario) -> bool:
        if usuario is None or not getattr(usuario, "is_authenticated", False):
            return False
        if usuario.is_admin:
            return True
        if self.usuario_id == usuario.id:
            return True
        return any(c.id == usuario.id for c in self.colaboradores)

    def __repr__(self):
        return f"<Disciplina {self.codigo} T{self.turma}>"


class AlunoDisciplina(db.Model):
    __tablename__ = "alunos_disciplina"

    id = db.Column(db.Integer, primary_key=True)
    disciplina_id = db.Column(db.Integer, db.ForeignKey("disciplinas.id"), nullable=False)
    matricula = db.Column(db.String(20), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    faltas_sigaa = db.Column(db.Integer, default=0, nullable=False)
    situacao = db.Column(db.String(50), nullable=True)

    disciplina = db.relationship("Disciplina", back_populates="alunos")
    presencas = db.relationship(
        "Presenca", back_populates="aluno", lazy="dynamic", cascade="all, delete-orphan"
    )
    notas = db.relationship(
        "Nota", back_populates="aluno", lazy="dynamic", cascade="all, delete-orphan"
    )
    membros_grupo = db.relationship(
        "GrupoMembro", back_populates="aluno", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint("disciplina_id", "matricula", name="uq_aluno_disciplina_matricula"),
    )

    def __repr__(self):
        return f"<AlunoDisciplina {self.matricula}>"


class Aula(db.Model):
    __tablename__ = "aulas"

    id = db.Column(db.Integer, primary_key=True)
    disciplina_id = db.Column(db.Integer, db.ForeignKey("disciplinas.id"), nullable=False)
    data = db.Column(db.Date, nullable=False)
    numero = db.Column(db.Integer, nullable=True)
    conteudo = db.Column(db.String(500), nullable=True)

    disciplina = db.relationship("Disciplina", back_populates="aulas")
    presencas = db.relationship(
        "Presenca", back_populates="aula", lazy="dynamic", cascade="all, delete-orphan"
    )

    __table_args__ = (
        db.UniqueConstraint("disciplina_id", "data", name="uq_aula_disciplina_data"),
    )


class Presenca(db.Model):
    __tablename__ = "presencas"

    STATUS_PRESENTE = "P"
    STATUS_AUSENTE = "A"
    STATUS_JUSTIFICADO = "J"
    STATUS_MANUAL = "manual"
    STATUS_AUTOMATICO = "automatico"

    id = db.Column(db.Integer, primary_key=True)
    aula_id = db.Column(db.Integer, db.ForeignKey("aulas.id"), nullable=False)
    aluno_disciplina_id = db.Column(
        db.Integer, db.ForeignKey("alunos_disciplina.id"), nullable=False
    )
    status = db.Column(db.String(1), nullable=False, default=STATUS_PRESENTE)
    origem = db.Column(db.String(20), nullable=False, default=STATUS_MANUAL)

    aula = db.relationship("Aula", back_populates="presencas")
    aluno = db.relationship("AlunoDisciplina", back_populates="presencas")

    __table_args__ = (
        db.UniqueConstraint("aula_id", "aluno_disciplina_id", name="uq_presenca_aula_aluno"),
    )


class Avaliacao(db.Model):
    __tablename__ = "avaliacoes"

    COLUNA_UNID1 = "Unid. 1"
    COLUNA_UNID2 = "Unid. 2"
    COLUNA_REC = "Rec."
    COLUNAS_SIGAA = (COLUNA_UNID1, COLUNA_UNID2, COLUNA_REC)

    id = db.Column(db.Integer, primary_key=True)
    disciplina_id = db.Column(db.Integer, db.ForeignKey("disciplinas.id"), nullable=False)
    nome = db.Column(db.String(50), nullable=False)
    peso = db.Column(db.Float, default=1.0, nullable=False)
    ordem = db.Column(db.Integer, default=0, nullable=False)
    coluna_sigaa = db.Column(db.String(20), nullable=False, default=COLUNA_UNID1)
    em_grupo = db.Column(db.Boolean, default=False, nullable=False)

    disciplina = db.relationship("Disciplina", back_populates="avaliacoes")
    notas = db.relationship(
        "Nota", back_populates="avaliacao", lazy="dynamic", cascade="all, delete-orphan"
    )
    grupos = db.relationship(
        "Grupo", back_populates="avaliacao", lazy="dynamic", cascade="all, delete-orphan"
    )


class Nota(db.Model):
    __tablename__ = "notas"

    id = db.Column(db.Integer, primary_key=True)
    avaliacao_id = db.Column(db.Integer, db.ForeignKey("avaliacoes.id"), nullable=False)
    aluno_disciplina_id = db.Column(
        db.Integer, db.ForeignKey("alunos_disciplina.id"), nullable=False
    )
    valor = db.Column(db.Float, nullable=True)

    avaliacao = db.relationship("Avaliacao", back_populates="notas")
    aluno = db.relationship("AlunoDisciplina", back_populates="notas")

    __table_args__ = (
        db.UniqueConstraint("avaliacao_id", "aluno_disciplina_id", name="uq_nota_avaliacao_aluno"),
    )


class Grupo(db.Model):
    """Grupo de alunos: avaliacao_id NULL = padrão da disciplina."""

    __tablename__ = "grupos"

    id = db.Column(db.Integer, primary_key=True)
    disciplina_id = db.Column(db.Integer, db.ForeignKey("disciplinas.id"), nullable=False)
    avaliacao_id = db.Column(db.Integer, db.ForeignKey("avaliacoes.id"), nullable=True)
    nome = db.Column(db.String(80), nullable=False)
    ordem = db.Column(db.Integer, default=0, nullable=False)

    disciplina = db.relationship("Disciplina", back_populates="grupos")
    avaliacao = db.relationship("Avaliacao", back_populates="grupos")
    membros = db.relationship(
        "GrupoMembro", back_populates="grupo", lazy="selectin", cascade="all, delete-orphan"
    )


class GrupoMembro(db.Model):
    __tablename__ = "grupo_membros"

    id = db.Column(db.Integer, primary_key=True)
    grupo_id = db.Column(db.Integer, db.ForeignKey("grupos.id"), nullable=False)
    aluno_disciplina_id = db.Column(
        db.Integer, db.ForeignKey("alunos_disciplina.id"), nullable=False
    )

    grupo = db.relationship("Grupo", back_populates="membros")
    aluno = db.relationship("AlunoDisciplina", back_populates="membros_grupo")

    __table_args__ = (
        db.UniqueConstraint("grupo_id", "aluno_disciplina_id", name="uq_grupo_aluno"),
    )
