from flask_wtf import FlaskForm
from wtforms import BooleanField, PasswordField, SelectField, StringField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError

from app.models import Usuario


class SetupForm(FlaskForm):
    nome = StringField("Nome completo", validators=[DataRequired(), Length(max=120)])
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=120)])
    senha = PasswordField(
        "Senha",
        validators=[DataRequired(), Length(min=8, message="A senha deve ter pelo menos 8 caracteres.")],
    )
    confirmar_senha = PasswordField(
        "Confirmar senha",
        validators=[DataRequired(), EqualTo("senha", message="As senhas devem coincidir.")],
    )
    submit = SubmitField("Criar conta administrador")


class LoginForm(FlaskForm):
    email = StringField("E-mail", validators=[DataRequired(), Email()])
    senha = PasswordField("Senha", validators=[DataRequired()])
    submit = SubmitField("Entrar")


class UsuarioForm(FlaskForm):
    nome = StringField("Nome completo", validators=[DataRequired(), Length(max=120)])
    email = StringField("E-mail", validators=[DataRequired(), Email(), Length(max=120)])
    senha = PasswordField(
        "Senha",
        validators=[Length(min=8, message="A senha deve ter pelo menos 8 caracteres.")],
    )
    confirmar_senha = PasswordField("Confirmar senha")
    papel = SelectField(
        "Papel",
        choices=[
            (Usuario.PAPEL_PROFESSOR, "Professor"),
            (Usuario.PAPEL_ADMIN, "Administrador"),
        ],
        validators=[DataRequired()],
    )
    ativo = BooleanField("Ativo", default=True)
    submit = SubmitField("Salvar")

    def validate_email(self, field):
        existing = Usuario.query.filter_by(email=field.data.lower().strip()).first()
        if existing and (not hasattr(self, "usuario_id") or existing.id != self.usuario_id):
            raise ValidationError("Este e-mail já está cadastrado.")

    def validate_confirmar_senha(self, field):
        if self.senha.data and self.senha.data != field.data:
            raise ValidationError("As senhas devem coincidir.")
