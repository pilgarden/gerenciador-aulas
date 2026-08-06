from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    IntegerField,
    SelectField,
    SelectMultipleField,
    StringField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class RelatorioPdfForm(FlaskForm):
    tipo = SelectField(
        "Conteúdo",
        choices=[
            ("notas", "Notas"),
            ("faltas", "Faltas"),
            ("ambos", "Notas e faltas"),
        ],
        validators=[DataRequired()],
        default="notas",
    )
    matricula_modo = SelectField(
        "Matrícula",
        choices=[
            ("completa", "Completa"),
            ("parcial", "Apenas últimos dígitos"),
        ],
        validators=[DataRequired()],
        default="parcial",
    )
    digitos_matricula = IntegerField(
        "Quantidade de dígitos finais",
        validators=[Optional(), NumberRange(min=2, max=8)],
        default=4,
    )
    incluir_nome = BooleanField("Incluir nome do aluno", default=True)
    incluir_media = BooleanField("Incluir coluna de média", default=True)
    avaliacoes = SelectMultipleField(
        "Avaliações a incluir (vazio = todas)",
        coerce=int,
        validators=[Optional()],
    )
    cabecalho = SelectField(
        "Cabeçalho",
        choices=[("simples", "Cabeçalho simples / personalizado")],
        validators=[DataRequired()],
        default="simples",
    )
    titulo_custom = StringField(
        "Título do relatório (opcional)",
        validators=[Optional(), Length(max=120)],
    )
    linha1 = StringField("Linha 1 do cabeçalho", validators=[Optional(), Length(max=200)])
    linha2 = StringField("Linha 2 do cabeçalho", validators=[Optional(), Length(max=200)])
    linha3 = StringField("Linha 3 do cabeçalho", validators=[Optional(), Length(max=200)])
    submit = SubmitField("Gerar PDF")
