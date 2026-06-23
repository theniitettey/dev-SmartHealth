"""
Smart Health Sync — Centralised Configuration
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026
"""

import os
from pathlib import Path

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

    # Database
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "sqlite:///" + str(BASE_DIR / "smarthealth.db"))
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Rate limiting
    RATELIMIT_STORAGE_URI = os.environ.get("REDIS_URL", "memory://")
    RATELIMIT_DEFAULT = "200 per day;50 per hour;10 per minute"

    # Logging
    LOG_LEVEL        = os.environ.get("LOG_LEVEL", "INFO")

    # Groq API
    GROQ_API_KEY     = os.environ.get("GROQ_API_KEY", "")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SECRET_KEY = os.environ.get("SECRET_KEY")  # Must be set in prod


def get_config():
    env = os.environ.get("FLASK_ENV", "development")
    return ProductionConfig() if env == "production" else DevelopmentConfig()
