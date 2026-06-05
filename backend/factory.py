"""
Smart Health Sync — Flask Application Factory
Author: Enock Queenson Eduafo | University of Ghana 2026
"""

import logging
import os
from flask import Flask
from flask_cors import CORS
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from backend.config import get_config
from backend.database.models import db

# Singletons for extensions
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)


def configure_logging(level: str = "INFO"):
    """Set up structured logging for the application."""
    numeric = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(
        level=numeric,
        format="%(asctime)s | %(levelname)-8s | %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def create_app() -> Flask:
    """Application factory — returns a fully configured Flask instance."""
    cfg = get_config()
    configure_logging(cfg.LOG_LEVEL)
    log = logging.getLogger("smarthealth.factory")

    # ── Path Resolution ──
    root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    template_dir = os.path.join(root_dir, "frontend", "templates")
    static_dir = os.path.join(root_dir, "frontend", "static")

    # ── Create Flask app ──
    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
        static_url_path="/static",
    )
    app.config.from_object(cfg)
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0  # never cache static files in dev

    # ── Extensions ────────────────────────────────────────────
    CORS(app, resources={r"/api/*": {"origins": cfg.CORS_ORIGINS}})
    db.init_app(app)
    migrate.init_app(app, db)
    
    # Configure Limiter
    limiter.init_app(app)
    app.config["RATELIMIT_STORAGE_URI"] = cfg.RATELIMIT_STORAGE_URI
    app.config["RATELIMIT_DEFAULT"] = cfg.RATELIMIT_DEFAULT

    # Ensure DB tables exist (Dev only)
    if cfg.DEBUG:
        with app.app_context():
            db.create_all()
            log.info("[SmartHealth] Database tables synchronised.")

    # ── Error Handlers ────────────────────────────────────────
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {"error": "Rate limit exceeded", "details": str(e.description)}, 429

    # ── Register blueprints ───────────────────────────────────
    from backend.api.routes import api_bp
    from backend.api.views  import views_bp
    app.register_blueprint(api_bp,   url_prefix="/api")
    app.register_blueprint(views_bp, url_prefix="")

    log.info(f"[SmartHealth] App created — ENV={cfg.FLASK_ENV}, DEBUG={cfg.DEBUG}")
    return app
