from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


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
    criado_em = db.Column(db.DateTime, default=utcnow, nullable=False)

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
    semestre_id = db.Column(db.Integer, db.ForeignKey("semestres.id"), nullable=False)
    codigo = db.Column(db.String(20), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    turma = db.Column(db.String(10), nullable=False, default="01")
    carga_horaria = db.Column(db.Integer, nullable=True)
    aulas_previstas = db.Column(db.Integer, nullable=True)

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

    __table_args__ = (
        db.UniqueConstraint("semestre_id", "codigo", "turma", name="uq_disciplina_semestre_codigo_turma"),
    )

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

    id = db.Column(db.Integer, primary_key=True)
    disciplina_id = db.Column(db.Integer, db.ForeignKey("disciplinas.id"), nullable=False)
    nome = db.Column(db.String(50), nullable=False)
    peso = db.Column(db.Float, default=1.0, nullable=False)
    ordem = db.Column(db.Integer, default=0, nullable=False)

    disciplina = db.relationship("Disciplina", back_populates="avaliacoes")
    notas = db.relationship(
        "Nota", back_populates="avaliacao", lazy="dynamic", cascade="all, delete-orphan"
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
