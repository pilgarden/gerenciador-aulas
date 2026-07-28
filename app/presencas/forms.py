from flask_wtf import FlaskForm
from wtforms import DateField, IntegerField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

from app.models import Aula


class AulaForm(FlaskForm):
    data = DateField("Data da aula", validators=[DataRequired()], format="%Y-%m-%d")
    numero = IntegerField("Número da aula", validators=[Optional(), NumberRange(min=1, max=500)])
    conteudo = TextAreaField("Conteúdo (opcional)", validators=[Optional(), Length(max=500)])
    submit = SubmitField("Salvar")

    def validate(self, extra_validators=None):
        if not super().validate(extra_validators):
            return False
        if hasattr(self, "disciplina_id") and self.data.data:
            existing = Aula.query.filter_by(
                disciplina_id=self.disciplina_id,
                data=self.data.data,
            ).first()
            if existing and (not hasattr(self, "aula_id") or existing.id != self.aula_id):
                self.data.errors.append("Já existe uma aula registrada nesta data.")
                return False
        return True
