from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_user, logout_user, login_required, current_user

from app.extensions import db
from app.models import Usuario
from app.auth.forms import LoginForm, SetupForm

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/setup", methods=["GET", "POST"])
def setup():
    if Usuario.query.count() > 0:
        flash("O sistema já foi configurado. Faça login.", "info")
        return redirect(url_for("auth.login"))

    form = SetupForm()
    if form.validate_on_submit():
        admin = Usuario(
            nome=form.nome.data.strip(),
            email=form.email.data.lower().strip(),
            papel=Usuario.PAPEL_ADMIN,
            ativo=True,
        )
        admin.set_senha(form.senha.data)
        db.session.add(admin)
        db.session.commit()
        flash("Conta administrador criada com sucesso! Faça login.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/setup.html", form=form)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if Usuario.query.count() == 0:
        return redirect(url_for("auth.setup"))

    if current_user.is_authenticated:
        return redirect(url_for("main.index"))

    form = LoginForm()
    if form.validate_on_submit():
        usuario = Usuario.query.filter_by(email=form.email.data.lower().strip()).first()
        if usuario is None or not usuario.check_senha(form.senha.data):
            flash("E-mail ou senha incorretos.", "danger")
        elif not usuario.ativo:
            flash("Esta conta está desativada.", "warning")
        else:
            login_user(usuario)
            next_page = url_for("main.index")
            flash(f"Bem-vindo, {usuario.nome}!", "success")
            return redirect(next_page)

    return render_template("auth/login.html", form=form)


@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Você saiu do sistema.", "info")
    return redirect(url_for("auth.login"))
