from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required, current_user

from app import admin_required
from app.extensions import db
from app.models import Usuario
from app.auth.forms import UsuarioForm

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")


@usuarios_bp.route("/")
@login_required
@admin_required
def listar():
    usuarios = Usuario.query.order_by(Usuario.nome).all()
    return render_template("usuarios/list.html", usuarios=usuarios)


@usuarios_bp.route("/novo", methods=["GET", "POST"])
@login_required
@admin_required
def novo():
    form = UsuarioForm()
    if form.validate_on_submit():
        if not form.senha.data:
            flash("Informe uma senha para o novo usuário.", "danger")
        else:
            usuario = Usuario(
                nome=form.nome.data.strip(),
                email=form.email.data.lower().strip(),
                papel=form.papel.data,
                ativo=form.ativo.data,
            )
            usuario.set_senha(form.senha.data)
            db.session.add(usuario)
            db.session.commit()
            flash("Usuário criado com sucesso.", "success")
            return redirect(url_for("usuarios.listar"))

    return render_template("usuarios/form.html", form=form, titulo="Novo usuário")


@usuarios_bp.route("/<int:usuario_id>/editar", methods=["GET", "POST"])
@login_required
@admin_required
def editar(usuario_id):
    usuario = db.session.get(Usuario, usuario_id)
    if usuario is None:
        flash("Usuário não encontrado.", "danger")
        return redirect(url_for("usuarios.listar"))

    form = UsuarioForm(obj=usuario)
    form.usuario_id = usuario.id

    if form.validate_on_submit():
        if usuario.id == current_user.id and form.papel.data != Usuario.PAPEL_ADMIN:
            flash("Você não pode remover seu próprio papel de administrador.", "danger")
        elif usuario.id == current_user.id and not form.ativo.data:
            flash("Você não pode desativar sua própria conta.", "danger")
        else:
            usuario.nome = form.nome.data.strip()
            usuario.email = form.email.data.lower().strip()
            usuario.papel = form.papel.data
            usuario.ativo = form.ativo.data
            if form.senha.data:
                usuario.set_senha(form.senha.data)
            db.session.commit()
            flash("Usuário atualizado.", "success")
            return redirect(url_for("usuarios.listar"))

    return render_template(
        "usuarios/form.html",
        form=form,
        titulo=f"Editar: {usuario.nome}",
        usuario=usuario,
    )
