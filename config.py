import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-key-altere-em-producao")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    WTF_CSRF_ENABLED = True
    # Pool adequado ao Neon (pooler) — evita abrir conexão a cada request
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "pool_size": 5,
        "max_overflow": 5,
    }

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{BASE_DIR / 'instance' / 'gerenciador.db'}",
    )
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
    }


class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "")
    SESSION_COOKIE_SECURE = True

    @staticmethod
    def init_app(app):
        uri = app.config.get("SQLALCHEMY_DATABASE_URI", "")
        # Neon / Heroku às vezes usam postgres://
        if uri.startswith("postgres://"):
            uri = uri.replace("postgres://", "postgresql://", 1)
        # channel_binding pode atrasar/falhar em alguns drivers; remove se presente
        if "channel_binding=" in uri:
            from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

            parsed = urlparse(uri)
            qs = [(k, v) for k, v in parse_qsl(parsed.query) if k != "channel_binding"]
            uri = urlunparse(parsed._replace(query=urlencode(qs)))
        app.config["SQLALCHEMY_DATABASE_URI"] = uri
        if not uri:
            raise ValueError("DATABASE_URL é obrigatória em produção.")


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
