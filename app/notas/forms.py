from flask_wtf import FlaskForm
from wtforms import FloatField, IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

from app.models import Avaliacao


class AvaliacaoForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=50)])
    peso = FloatField("Peso", validators=[Optional(), NumberRange(min=0.1, max=10)], default=1.0)
    ordem = IntegerField("Ordem", validators=[Optional(), NumberRange(min=0, max=100)])
    submit = SubmitField("Salvar")

    def validate_nome(self, field):
        if not hasattr(self, "disciplina_id"):
            return
        existing = Avaliacao.query.filter_by(
            disciplina_id=self.disciplina_id,
            nome=field.data.strip(),
        ).first()
        if existing and (not hasattr(self, "avaliacao_id") or existing.id != self.avaliacao_id):
            raise ValidationError("Já existe uma avaliação com este nome nesta disciplina.")
