"""
Smart Health Sync — HTML Page Views Blueprint
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026
"""

from flask import Blueprint, render_template, request

views_bp = Blueprint("views", __name__)


@views_bp.route("/")
def index():
    """Landing page — hero, stats, workflow, conditions."""
    return render_template("index.html")


@views_bp.route("/predict")
def predict_page():
    """Diagnosis input page — 24 biomarkers form."""
    return render_template("predict.html")


@views_bp.route("/results")
def results_page():
    """Model evaluation metrics and benchmarks page."""
    return render_template("results.html")


@views_bp.route("/about")
def about_page():
    """Project info and researcher details page."""
    return render_template("about.html")


# ── Context processors ───────────────────────────────────────
@views_bp.app_context_processor
def inject_globals():
    """Inject global template variables."""
    return {
        "current_path": request.path,
        "project_name": "Smart Health Sync",
    }
