from flask_wtf import FlaskForm
from wtforms import FileField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

from app.models import Disciplina, Semestre


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
        usuario_id = getattr(self, "usuario_id", None)
        if usuario_id is None:
            self.codigo.errors.append("Usuário dono da disciplina não definido.")
            return False
        existing = Disciplina.query.filter_by(
            usuario_id=usuario_id,
            semestre_id=self.semestre_id.data,
            codigo=self.codigo.data.strip(),
            turma=self.turma.data.strip(),
        ).first()
        if existing and (not hasattr(self, "disciplina_id") or existing.id != self.disciplina_id):
            self.codigo.errors.append(
                "Você já tem uma disciplina com este código e turma neste semestre."
            )
            return False
        return True


class ImportSigaaForm(FlaskForm):
    arquivo = FileField("Planilha SIGAA (.xls)", validators=[DataRequired()])
    submit = SubmitField("Analisar planilha")
