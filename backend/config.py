"""
Smart Health Sync — Centralised Configuration
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026
"""

import os
from pathlib import Path

# Load .env file manually if it exists to avoid python-dotenv dependency
def load_env_file():
    base_dir = Path(__file__).resolve().parent.parent
    env_path = base_dir / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    val = v.strip()
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    os.environ.setdefault(k.strip(), val)

load_env_file()

# ─── Base Paths ───────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
BACKEND_DIR = Path(__file__).resolve().parent
MODELS_DIR  = BASE_DIR / "models"
STATIC_DIR  = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

# ─── Environment ─────────────────────────────────────────────
class Config:
    SECRET_KEY       = os.environ.get("SECRET_KEY", "smarthealthsync-dev-secret-2026")
    FLASK_ENV        = os.environ.get("FLASK_ENV", "development")
    DEBUG            = FLASK_ENV != "production"
    PORT             = int(os.environ.get("PORT", 5000))

    # Model paths
    MODELS_DIR       = MODELS_DIR
    MODEL_STORAGE    = os.environ.get("MODEL_STORAGE_PATH", str(MODELS_DIR))
    MODEL_DOWNLOAD_URL = os.environ.get("MODEL_DOWNLOAD_URL", "")

    # Required model binaries
    REQUIRED_MODELS  = [
        "random_forest.pkl",
        "support_vector_machine.pkl",
        "decision_tree.pkl",
        "logistic_regression.pkl",
        "scaler.pkl",
        "label_encoder.pkl",
        "results_summary.json",
    ]

    # CORS
    CORS_ORIGINS     = os.environ.get("CORS_ORIGINS", "*")

    # Database — DATABASE_URL is required; no SQLite fallback to prevent silent data loss
    _db_url = os.environ.get("DATABASE_URL")
    if not _db_url:
        raise RuntimeError(
            "DATABASE_URL is not set. "
            "Provide a valid PostgreSQL connection string in your environment or .env file."
        )
    if _db_url.startswith("postgres://"):
        _db_url = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Rate limiting
    RATELIMIT_STORAGE_URI = os.environ.get("REDIS_URL", "memory://")
    RATELIMIT_DEFAULT = "200 per day;50 per hour;10 per minute"

    # Logging
    LOG_LEVEL        = os.environ.get("LOG_LEVEL", "INFO")

    # Groq API
    GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")

    # Admin seed credentials
    ADMIN_EMAIL      = os.environ.get("ADMIN_EMAIL", "admin@smarthealth.com")
    ADMIN_USERNAME   = os.environ.get("ADMIN_USERNAME", "admin@smarthealth.com")
    ADMIN_PASSWORD   = os.environ.get("ADMIN_PASSWORD", "AdminPassword2026")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get("SECRET_KEY")  # Must be set in prod


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return ProductionConfig() if env == "production" else DevelopmentConfig()
