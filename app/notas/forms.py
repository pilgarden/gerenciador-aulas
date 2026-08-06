from flask_wtf import FlaskForm
from wtforms import BooleanField, FloatField, IntegerField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Length, NumberRange, Optional, ValidationError

from app.models import Avaliacao


class AvaliacaoForm(FlaskForm):
    nome = StringField("Nome", validators=[DataRequired(), Length(max=50)])
    coluna_sigaa = SelectField(
        "Coluna SIGAA (exportação)",
        choices=[
            (Avaliacao.COLUNA_UNID1, "Unid. 1"),
            (Avaliacao.COLUNA_UNID2, "Unid. 2"),
            (Avaliacao.COLUNA_REC, "Rec."),
        ],
        validators=[DataRequired()],
        default=Avaliacao.COLUNA_UNID1,
    )
    peso = FloatField("Peso", validators=[Optional(), NumberRange(min=0.1, max=10)], default=1.0)
    ordem = IntegerField("Ordem", validators=[Optional(), NumberRange(min=0, max=100)])
    em_grupo = BooleanField("Avaliação em grupo", default=False)
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
