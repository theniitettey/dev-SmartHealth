"""
Smart Health Sync — Flask Application Factory
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026
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


def _rebuild_diagnostic_records_table(col_info):
    """SQLite rebuild so patient_id can be NULL (legacy schema enforced NOT NULL)."""
    from sqlalchemy import text

    new_cols = [
        "id", "patient_id", "user_id", "patient_reference", "biomarkers_json",
        "result_json", "prediction_label", "confidence_score", "model_version", "created_at",
    ]
    copy_cols = [c for c in new_cols if c in col_info]

    db.session.execute(text("""
        CREATE TABLE diagnostic_records_migrated (
            id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            user_id INTEGER NOT NULL,
            patient_reference VARCHAR(64),
            biomarkers_json TEXT,
            result_json TEXT,
            prediction_label VARCHAR(64) NOT NULL,
            confidence_score FLOAT NOT NULL,
            model_version VARCHAR(32),
            created_at DATETIME,
            FOREIGN KEY(patient_id) REFERENCES patients (id),
            FOREIGN KEY(user_id) REFERENCES users (id)
        )
    """))

    if copy_cols:
        cols_sql = ", ".join(copy_cols)
        db.session.execute(text(f"""
            INSERT INTO diagnostic_records_migrated ({cols_sql})
            SELECT {cols_sql} FROM diagnostic_records
            WHERE user_id IS NOT NULL
        """))

    db.session.execute(text("DROP TABLE diagnostic_records"))
    db.session.execute(text("ALTER TABLE diagnostic_records_migrated RENAME TO diagnostic_records"))
    db.session.commit()


def _ensure_diagnostic_schema():
    """Migrate diagnostic_records schema on existing SQLite databases."""
    from sqlalchemy import inspect, text

    log = logging.getLogger("smarthealth.factory")
    try:
        insp = inspect(db.engine)
        if "diagnostic_records" not in insp.get_table_names():
            return

        pragma_rows = db.session.execute(text("PRAGMA table_info(diagnostic_records)")).fetchall()
        col_info = {row[1]: row for row in pragma_rows}

        additions = {
            "patient_reference": "VARCHAR(64)",
            "biomarkers_json": "TEXT",
            "result_json": "TEXT",
        }
        for name, col_type in additions.items():
            if name not in col_info:
                db.session.execute(
                    text(f"ALTER TABLE diagnostic_records ADD COLUMN {name} {col_type}")
                )
        db.session.commit()

        patient_row = col_info.get("patient_id")
        if patient_row and patient_row[3] == 1:
            log.info("[SmartHealth] Migrating diagnostic_records (patient_id → nullable).")
            _rebuild_diagnostic_records_table(col_info)
    except Exception as exc:
        db.session.rollback()
        log.warning(f"Schema migration skipped: {exc}")


def _ensure_patient_schema():
    """Add user_id column to patients table for registered patient accounts."""
    from sqlalchemy import inspect, text

    log = logging.getLogger("smarthealth.factory")
    try:
        insp = inspect(db.engine)
        if "patients" not in insp.get_table_names():
            return
        cols = {c["name"] for c in insp.get_columns("patients")}
        if "user_id" not in cols:
            log.info("[SmartHealth] Adding patients.user_id column.")
            db.session.execute(text("ALTER TABLE patients ADD COLUMN user_id INTEGER UNIQUE"))
            db.session.commit()
    except Exception as exc:
        db.session.rollback()
        log.warning(f"Patient schema migration skipped: {exc}")


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

    # Configure uploads folder
    upload_dir = os.path.join(static_dir, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    app.config["UPLOAD_FOLDER"] = upload_dir

    # Ensure DB tables exist and seed default admin user
    with app.app_context():
        db.create_all()
        _ensure_diagnostic_schema()
        _ensure_patient_schema()
        log.info("[SmartHealth] Database tables synchronised.")
        
        from backend.database.models import User
        admin = User.query.filter_by(role='admin').first()
        if not admin:
            admin = User(
                username='admin@smarthealth.com',
                email='admin@smarthealth.com',
                full_name='Super Admin',
                role='admin',
                status='approved'
            )
            admin.set_password('AdminPassword2026')
            db.session.add(admin)
            db.session.commit()
            log.info("[SmartHealth] Seeded default Super Admin: admin@smarthealth.com")

    # ── Error Handlers ────────────────────────────────────────
    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {"error": "Rate limit exceeded", "details": str(e.description)}, 429

    # ── Register blueprints ───────────────────────────────────
    from backend.api.routes import api_bp
    from backend.api.views  import views_bp
    from backend.api.auth   import auth_bp
    app.register_blueprint(api_bp,   url_prefix="/api")
    app.register_blueprint(views_bp, url_prefix="")
    app.register_blueprint(auth_bp,  url_prefix="/api/auth")

    log.info(f"[SmartHealth] App created — ENV={cfg.FLASK_ENV}, DEBUG={cfg.DEBUG}")
    return app
