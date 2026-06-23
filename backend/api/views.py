"""
Smart Health Sync — HTML Page Views Blueprint
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026
"""

from flask import Blueprint, render_template, request, session, redirect, url_for
from backend.database.models import User, Patient, DiagnosticRecord, DoctorPatientConnection
from backend.ml.model_manager import model_manager

views_bp = Blueprint("views", __name__)
ADMIN_SECTIONS = ("dashboard", "verification", "users", "datasets", "monitoring", "view_record")
DOCTOR_SECTIONS = ("dashboard", "profile", "history", "reports", "patients", "view_record")

SECTION_TITLES = {
    "dashboard": ("Dashboard", "Overview and key metrics"),
    "verification": ("Doctor Verification", "Review and approve practitioner credentials"),
    "users": ("Doctor Management", "Manage registered medical accounts"),
    "datasets": ("Dataset Management", "View and replace active clinical training files"),
    "monitoring": ("System Monitoring", "Platform health and model status"),
    "diagnosis": ("Patient Diagnosis", "Enter biomarker data and run clinical prediction"),
    "profile": ("Profile", "Your account details"),
    "history": ("Diagnosis History", "Past diagnostic sessions and outcomes"),
    "reports": ("Downloadable Reports", "Print and export diagnosis reports"),
    "patients": ("Patient Cases", "Manage patient cases and records"),
    "view_record": ("Medical Report", "Detailed clinical diagnostic insights"),
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
    return redirect(url_for("views.register_doctor_page"))


@views_bp.route("/register/doctor")
def register_doctor_page():
    if session.get("role"):
        return redirect(url_for("views.portal_page"))
    return render_template("register_doctor.html")


@views_bp.route("/register/patient")
def register_patient_page():
    return redirect(url_for("views.register_doctor_page"))


@views_bp.route("/register/technician")
def register_technician_page():
    return redirect(url_for("views.register_doctor_page"))


def _portal_stats(doctors, all_users, records):
    doctors_list = [d for d in doctors if d.role == "doctor"]
    pending = sum(1 for d in doctors_list if d.status == "pending")
    approved = sum(1 for d in doctors_list if d.status == "approved")
    rejected = sum(1 for d in doctors_list if d.status == "rejected")
    
    from backend.database.models import Patient, DiagnosticRecord
    total_cases = Patient.query.count()
    total_predictions = DiagnosticRecord.query.count()
    generated_reports = DiagnosticRecord.query.filter_by(status="approved").count()
    
    return {
        "total_doctors": len(doctors_list),
        "total_patients": total_cases,
        "total_cases": total_cases,
        "pending_count": pending,
        "approved_count": approved,
        "rejected_count": rejected,
        "total_users": len(all_users),
        "total_diagnoses": total_predictions,
        "total_predictions": total_predictions,
        "generated_reports": generated_reports,
    }

def _build_portal_context(user_id, role, section):
    page_title, page_subtitle = SECTION_TITLES.get(section, ("Portal", ""))

    from flask import request
    record = None
    record_id = request.args.get("record_id", type=int)
    if record_id:
        record = DiagnosticRecord.query.get(record_id)

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
            "record": record,
        }

    # Otherwise: Doctor
    doctor = User.query.get(user_id)
    if doctor:
        session["status"] = doctor.status

    records = (
        DiagnosticRecord.query.filter_by(user_id=user_id)
        .order_by(DiagnosticRecord.created_at.desc())
        .all()
    )
    
    patients = Patient.query.filter_by(doctor_id=user_id).order_by(Patient.created_at.desc()).all()
    active_patients = [p for p in patients if not p.is_archived]
    archived_patients = [p for p in patients if p.is_archived]

    return {
        "section": section,
        "doctor": doctor,
        "records": records,
        "patients": patients,
        "active_patients": active_patients,
        "archived_patients": archived_patients,
        "stats": {
            "total_diagnoses": len(records),
            "total_patients": len(active_patients),
            "pending_count": len(records),
            "approved_count": len(active_patients),
            "rejected_count": 1 if doctor and doctor.status == "rejected" else 0,
            "total_doctors": 0,
            "total_users": 0,
        },
        "doctors": [],
        "all_users": [],
        "health": None,
        "patient_user": None,
        "patient_profile": None,
        "page_title": page_title,
        "page_subtitle": page_subtitle,
        "record": record,
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
