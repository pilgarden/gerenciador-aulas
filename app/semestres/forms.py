from flask_wtf import FlaskForm
from wtforms import BooleanField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError

from app.models import Semestre


class SemestreForm(FlaskForm):
    codigo = StringField(
        "Código",
        validators=[DataRequired(), Length(max=10)],
        render_kw={"placeholder": "2026.2"},
    )
    ativo = BooleanField("Semestre ativo", default=True)
    submit = SubmitField("Salvar")

    def validate_codigo(self, field):
        codigo = field.data.strip()
        existing = Semestre.query.filter_by(codigo=codigo).first()
        if existing and (not hasattr(self, "semestre_id") or existing.id != self.semestre_id):
            raise ValidationError("Este semestre já está cadastrado.")
