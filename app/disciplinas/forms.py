from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    FileField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional

from app.models import Disciplina, Semestre, Usuario


class DisciplinaForm(FlaskForm):
    semestre_id = SelectField("Semestre", coerce=int, validators=[DataRequired()])
    codigo = StringField("Código", validators=[DataRequired(), Length(max=20)])
    nome = StringField("Nome", validators=[DataRequired(), Length(max=200)])
    turma = StringField("Turma", validators=[DataRequired(), Length(max=10)], default="01")
    carga_horaria = IntegerField(
        "Carga horária (h)",
        validators=[Optional(), NumberRange(min=1, max=500)],
    )
    aulas_previstas = IntegerField(
        "Aulas previstas",
        validators=[Optional(), NumberRange(min=1, max=500)],
    )
    submit = SubmitField("Salvar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.semestre_id.choices = [
            (s.id, s.codigo) for s in Semestre.query.order_by(Semestre.codigo.desc()).all()
        ]

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        if not self.semestre_id.choices:
            self.semestre_id.errors.append("Cadastre um semestre antes de criar disciplinas.")
            return False
        existing = Disciplina.query.filter_by(
            semestre_id=self.semestre_id.data,
            codigo=self.codigo.data.strip(),
            turma=self.turma.data.strip(),
        ).first()
        if existing and (not hasattr(self, "disciplina_id") or existing.id != self.disciplina_id):
            self.codigo.errors.append(
                "Já existe uma disciplina com este código e turma neste semestre. "
                "Peça ao admin para compartilhá-la se for o caso."
            )
            return False
        return True


class ProfessoresDisciplinaForm(FlaskForm):
    dono_id = SelectField("Dono da disciplina", coerce=int, validators=[DataRequired()])
    colaboradores = SelectMultipleField("Colaboradores", coerce=int, validators=[Optional()])
    manter_dono_anterior_como_colaborador = BooleanField(
        "Manter dono anterior como colaborador ao transferir",
        default=True,
    )
    submit = SubmitField("Salvar")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        usuarios = Usuario.query.filter_by(ativo=True).order_by(Usuario.nome).all()
        choices = [(u.id, f"{u.nome} ({u.email})") for u in usuarios]
        self.dono_id.choices = choices
        self.colaboradores.choices = choices


class ImportSigaaForm(FlaskForm):
    arquivo = FileField("Planilha SIGAA (.xls)", validators=[DataRequired()])
    submit = SubmitField("Analisar planilha")
