import os
from functools import wraps

from flask import Flask, redirect, url_for, flash
from flask_login import current_user

from config import config
from app.extensions import db, login_manager, migrate, csrf


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_CONFIG", "development")

    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    instance_path = app.instance_path
    os.makedirs(instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import Usuario

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Usuario, int(user_id))

    from app.auth.routes import auth_bp
    from app.main.routes import main_bp
    from app.usuarios.routes import usuarios_bp
    from app.semestres.routes import semestres_bp
    from app.disciplinas.routes import disciplinas_bp
    from app.alunos.routes import alunos_bp
    from app.presencas.routes import presencas_bp
    from app.notas.routes import notas_bp
    from app.estatisticas.routes import estatisticas_bp
    from app.relatorios import relatorios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(semestres_bp)
    app.register_blueprint(disciplinas_bp)
    app.register_blueprint(alunos_bp)
    app.register_blueprint(presencas_bp)
    app.register_blueprint(notas_bp)
    app.register_blueprint(estatisticas_bp)
    app.register_blueprint(relatorios_bp)

    @app.context_processor
    def inject_globals():
        return {"needs_setup": Usuario.query.count() == 0}

    return app


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("auth.login"))
        if not current_user.is_admin:
            flash("Acesso restrito a administradores.", "danger")
            return redirect(url_for("main.index"))
        return view(*args, **kwargs)

    return wrapped
