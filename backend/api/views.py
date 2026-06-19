"""
Smart Health Sync — HTML Page Views Blueprint
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026
"""

from flask import Blueprint, render_template, request, session, redirect, url_for
from backend.database.models import User, Patient, DiagnosticRecord
from backend.ml.model_manager import model_manager

views_bp = Blueprint("views", __name__)

ADMIN_SECTIONS = ("dashboard", "verification", "users", "access", "monitoring")
DOCTOR_SECTIONS = ("dashboard", "profile", "history", "reports")
PATIENT_SECTIONS = ("dashboard", "profile", "records", "reports")

SECTION_TITLES = {
    "dashboard": ("Dashboard", "Overview and key metrics"),
    "verification": ("Doctor Verification", "Review and approve practitioner credentials"),
    "users": ("User Management", "Manage registered accounts and roles"),
    "access": ("Access Control", "Role-based permissions and feature access"),
    "monitoring": ("System Monitoring", "Platform health and model status"),
    "diagnosis": ("Patient Diagnosis", "Enter biomarker data and run clinical prediction"),
    "profile": ("Profile", "Your account details"),
    "history": ("Diagnosis History", "Past diagnostic sessions and outcomes"),
    "records": ("My Health Records", "Diagnoses linked to your patient profile"),
    "reports": ("Downloadable Reports", "Print and export diagnosis reports"),
}


@views_bp.route("/")
def index():
    return render_template("index.html")


@views_bp.route("/predict")
def predict_page():
    user_id = session.get("user_id")
    role = session.get("role")
    status = session.get("status")

    if not role:
        return redirect(url_for("views.login_page"))

    if role != "admin" and (role != "doctor" or status != "approved"):
        return redirect(url_for("views.portal_page"))

    ctx = _build_portal_context(user_id, role, "diagnosis")
    return render_template("predict.html", **ctx)


@views_bp.route("/results")
def results_page():
    if session.get("user_id"):
        role = session.get("role")
        if role == "admin":
            return redirect(url_for("views.portal_page", section="monitoring"))
        if role == "patient":
            return redirect(url_for("views.portal_page", section="records"))
        return redirect(url_for("views.portal_page", section="history"))
    return render_template("results.html")


@views_bp.route("/about")
def about_page():
    return render_template("about.html")


@views_bp.route("/login")
def login_page():
    if session.get("role"):
        return redirect(url_for("views.portal_page"))
    return render_template("login.html")


@views_bp.route("/register")
def register_page():
    if session.get("role"):
        return redirect(url_for("views.portal_page"))
    return render_template("register.html")


@views_bp.route("/register/doctor")
def register_doctor_page():
    if session.get("role"):
        return redirect(url_for("views.portal_page"))
    return render_template("register_doctor.html")


@views_bp.route("/register/patient")
def register_patient_page():
    if session.get("role"):
        return redirect(url_for("views.portal_page"))
    return render_template("register_patient.html")


def _portal_stats(doctors, all_users, records):
    patients = [u for u in all_users if u.role == "patient"]
    pending = sum(1 for d in doctors if d.status == "pending")
    approved = sum(1 for d in doctors if d.status == "approved")
    rejected = sum(1 for d in doctors if d.status == "rejected")
    return {
        "total_doctors": len(doctors),
        "total_patients": len(patients),
        "pending_count": pending,
        "approved_count": approved,
        "rejected_count": rejected,
        "total_users": len(all_users),
        "total_diagnoses": len(records),
    }


def _build_portal_context(user_id, role, section):
    page_title, page_subtitle = SECTION_TITLES.get(section, ("Portal", ""))

    if role == "admin":
        doctors = User.query.filter_by(role="doctor").order_by(User.created_at.desc()).all()
        all_users = User.query.order_by(User.created_at.desc()).all()
        records = DiagnosticRecord.query.order_by(DiagnosticRecord.created_at.desc()).limit(50).all()
        return {
            "section": section,
            "doctors": doctors,
            "all_users": all_users,
            "records": records,
            "stats": _portal_stats(doctors, all_users, records),
            "health": model_manager.health_report(),
            "doctor": None,
            "patient_user": None,
            "patient_profile": None,
            "page_title": page_title,
            "page_subtitle": page_subtitle,
        }

    if role == "patient":
        patient_user = User.query.get(user_id)
        patient_profile = Patient.query.filter_by(user_id=user_id).first()
        records = []
        if patient_profile:
            records = (
                DiagnosticRecord.query.filter_by(patient_id=patient_profile.id)
                .order_by(DiagnosticRecord.created_at.desc())
                .all()
            )
        return {
            "section": section,
            "patient_user": patient_user,
            "patient_profile": patient_profile,
            "records": records,
            "stats": {
                "total_records": len(records),
                "pending_count": 0,
                "approved_count": 0,
                "rejected_count": 0,
                "total_doctors": 0,
                "total_patients": 0,
                "total_users": 0,
                "total_diagnoses": len(records),
            },
            "doctors": [],
            "all_users": [],
            "health": None,
            "doctor": None,
            "page_title": page_title,
            "page_subtitle": page_subtitle,
        }

    doctor = User.query.get(user_id)
    if doctor:
        session["status"] = doctor.status

    records = (
        DiagnosticRecord.query.filter_by(user_id=user_id)
        .order_by(DiagnosticRecord.created_at.desc())
        .all()
    )
    return {
        "section": section,
        "doctor": doctor,
        "records": records,
        "stats": {
            "total_diagnoses": len(records),
            "pending_count": 0,
            "approved_count": 1 if doctor and doctor.status == "approved" else 0,
            "rejected_count": 1 if doctor and doctor.status == "rejected" else 0,
            "total_doctors": 0,
            "total_patients": 0,
            "total_users": 0,
        },
        "doctors": [],
        "all_users": [],
        "health": None,
        "patient_user": None,
        "patient_profile": None,
        "page_title": page_title,
        "page_subtitle": page_subtitle,
    }


@views_bp.route("/portal")
def portal_page():
    user_id = session.get("user_id")
    role = session.get("role")

    if not user_id:
        return redirect(url_for("views.login_page"))

    section = request.args.get("section", "dashboard")

    if role == "admin":
        if section not in ADMIN_SECTIONS:
            section = "dashboard"
    elif role == "patient":
        if section not in PATIENT_SECTIONS:
            section = "dashboard"
    else:
        if section not in DOCTOR_SECTIONS:
            section = "dashboard"

    ctx = _build_portal_context(user_id, role, section)
    return render_template("portal.html", **ctx)


@views_bp.app_context_processor
def inject_globals():
    return {
        "current_path": request.path,
        "project_name": "Smart Health Sync",
        "session": session,
    }
