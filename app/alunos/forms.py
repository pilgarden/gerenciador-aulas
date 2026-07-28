from flask_wtf import FlaskForm
from wtforms import IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

from app.models import AlunoDisciplina


class AlunoForm(FlaskForm):
    matricula = StringField("Matrícula", validators=[DataRequired(), Length(max=20)])
    nome = StringField("Nome", validators=[DataRequired(), Length(max=200)])
    faltas_sigaa = IntegerField("Faltas (SIGAA)", validators=[Optional(), NumberRange(min=0)], default=0)
    situacao = StringField("Situação", validators=[Optional(), Length(max=50)])
    submit = SubmitField("Salvar")

    def validate_matricula(self, field):
        matricula = field.data.strip()
        if not matricula.isdigit():
            raise ValidationError("A matrícula deve conter apenas números.")
        if hasattr(self, "disciplina_id"):
            existing = AlunoDisciplina.query.filter_by(
                disciplina_id=self.disciplina_id,
                matricula=matricula,
            ).first()
            if existing and (not hasattr(self, "aluno_id") or existing.id != self.aluno_id):
                raise ValidationError("Esta matrícula já está cadastrada nesta disciplina.")
