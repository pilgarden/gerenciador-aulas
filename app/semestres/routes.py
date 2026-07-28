from flask import Blueprint, flash, redirect, render_template, url_for
from flask_login import login_required

from app.extensions import db
from app.models import Disciplina, Semestre
from app.semestres.forms import SemestreForm

semestres_bp = Blueprint("semestres", __name__, url_prefix="/semestres")


def _definir_semestre_ativo(semestre: Semestre):
    if semestre.ativo:
        Semestre.query.filter(Semestre.id != semestre.id).update({"ativo": False})


@semestres_bp.route("/")
@login_required
def listar():
    semestres = Semestre.query.order_by(Semestre.codigo.desc()).all()
    return render_template("semestres/list.html", semestres=semestres)


@semestres_bp.route("/novo", methods=["GET", "POST"])
@login_required
def novo():
    form = SemestreForm()
    if form.validate_on_submit():
        semestre = Semestre(codigo=form.codigo.data.strip(), ativo=form.ativo.data)
        db.session.add(semestre)
        _definir_semestre_ativo(semestre)
        db.session.commit()
        flash("Semestre criado com sucesso.", "success")
        return redirect(url_for("semestres.listar"))

    return render_template("semestres/form.html", form=form, titulo="Novo semestre")


@semestres_bp.route("/<int:semestre_id>/editar", methods=["GET", "POST"])
@login_required
def editar(semestre_id):
    semestre = db.session.get(Semestre, semestre_id)
    if semestre is None:
        flash("Semestre não encontrado.", "danger")
        return redirect(url_for("semestres.listar"))

    form = SemestreForm(obj=semestre)
    form.semestre_id = semestre.id

    if form.validate_on_submit():
        semestre.codigo = form.codigo.data.strip()
        semestre.ativo = form.ativo.data
        _definir_semestre_ativo(semestre)
        db.session.commit()
        flash("Semestre atualizado.", "success")
        return redirect(url_for("semestres.listar"))

    return render_template(
        "semestres/form.html",
        form=form,
        titulo=f"Editar semestre {semestre.codigo}",
        semestre=semestre,
    )


@semestres_bp.route("/<int:semestre_id>/excluir", methods=["POST"])
@login_required
def excluir(semestre_id):
    semestre = db.session.get(Semestre, semestre_id)
    if semestre is None:
        flash("Semestre não encontrado.", "danger")
        return redirect(url_for("semestres.listar"))

    if semestre.disciplinas.count() > 0:
        flash("Não é possível excluir um semestre com disciplinas cadastradas.", "warning")
        return redirect(url_for("semestres.listar"))

    db.session.delete(semestre)
    db.session.commit()
    flash("Semestre excluído.", "success")
    return redirect(url_for("semestres.listar"))
