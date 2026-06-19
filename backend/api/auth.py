"""
Smart Health Sync — Authentication & Verification Routes
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026
"""

import os
import uuid
import logging
import time
from datetime import datetime

from flask import Blueprint, request, jsonify, session, current_app
from werkzeug.utils import secure_filename

from backend.database.models import db, User, Patient

logger = logging.getLogger("smarthealth.auth")
auth_bp = Blueprint("auth", __name__)

ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def _split_name(full_name):
    parts = full_name.strip().split(None, 1)
    return parts[0], parts[1] if len(parts) > 1 else ""


def _set_user_session(user, patient_profile=None):
    session["user_id"] = user.id
    session["role"] = user.role
    session["full_name"] = user.full_name
    session["status"] = user.status
    if patient_profile:
        session["patient_id"] = patient_profile.id
    else:
        session.pop("patient_id", None)


# ── POST /register ───────────────────────────────────────────
@auth_bp.route("/register", methods=["POST"])
def register():
    try:
        account_type = request.form.get("account_type", "doctor").strip().lower()
        if account_type not in ("doctor", "patient"):
            return jsonify({"error": "Invalid account type. Choose doctor or patient."}), 400

        email = request.form.get("email", "").strip().lower()
        full_name = request.form.get("full_name", "").strip()
        password = request.form.get("password", "")

        if not email or not full_name or not password:
            return jsonify({"error": "Email, Full Name, and Password are required."}), 400

        if len(password) < 8:
            return jsonify({"error": "Password must be at least 8 characters."}), 400

        if User.query.filter_by(email=email).first():
            return jsonify({"error": "An account with this email address already exists."}), 400

        if account_type == "doctor":
            return _register_doctor(email, full_name, password)
        return _register_patient(email, full_name, password)

    except Exception as e:
        logger.exception(f"[Auth] Error during registration: {e}")
        return jsonify({"error": "Internal server error during registration."}), 500


def _register_doctor(email, full_name, password):
    hospital = request.form.get("hospital", "").strip() or None
    specialization = request.form.get("specialization", "").strip() or None

    if "proof" not in request.files:
        return jsonify({"error": "Proof of professionalism document is required."}), 400

    file = request.files["proof"]
    if file.filename == "":
        return jsonify({"error": "No proof file selected for upload."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file format. Allowed: PDF, PNG, JPG, JPEG, DOC, DOCX."}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{int(time.time())}_{filename}"
    upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_filename)
    file.save(upload_path)

    user = User(
        username=email,
        email=email,
        full_name=full_name,
        hospital=hospital,
        specialization=specialization,
        proof_filename=unique_filename,
        role="doctor",
        status="pending",
    )
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    _set_user_session(user)
    logger.info(f"[Auth] Doctor registered: {email}")
    return jsonify({
        "status": "success",
        "message": "Registration successful. Your account is pending verification.",
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role, "status": user.status},
    }), 201


def _register_patient(email, full_name, password):
    dob_str = request.form.get("date_of_birth", "").strip()
    gender = request.form.get("gender", "").strip() or None
    blood_group = request.form.get("blood_group", "").strip() or None

    if not dob_str:
        return jsonify({"error": "Date of birth is required for patient registration."}), 400

    try:
        dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Invalid date of birth. Use YYYY-MM-DD format."}), 400

    first_name, last_name = _split_name(full_name)
    if not last_name:
        last_name = first_name

    user = User(
        username=email,
        email=email,
        full_name=full_name,
        role="patient",
        status="approved",
    )
    user.set_password(password)
    db.session.add(user)
    db.session.flush()

    profile = Patient(
        user_id=user.id,
        patient_uuid=str(uuid.uuid4()),
        first_name=first_name,
        last_name=last_name,
        date_of_birth=dob,
        gender=gender,
        blood_group=blood_group,
    )
    db.session.add(profile)
    db.session.commit()

    _set_user_session(user, profile)
    logger.info(f"[Auth] Patient registered: {email}")
    return jsonify({
        "status": "success",
        "message": "Patient account created successfully.",
        "user": {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role, "status": user.status},
    }), 201


# ── POST /login ──────────────────────────────────────────────
@auth_bp.route("/login", methods=["POST"])
def login():
    try:
        data = request.get_json(force=True, silent=True) or {}
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")

        if not email or not password:
            return jsonify({"error": "Email and password are required."}), 400

        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            return jsonify({"error": "Invalid email address or password."}), 401

        patient_profile = None
        if user.role == "patient":
            patient_profile = Patient.query.filter_by(user_id=user.id).first()

        _set_user_session(user, patient_profile)

        logger.info(f"[Auth] User logged in: {email} (role: {user.role})")
        return jsonify({
            "status": "success",
            "message": "Login successful.",
            "user": {
                "id": user.id,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "status": user.status,
            },
        }), 200

    except Exception as e:
        logger.exception(f"[Auth] Error during login: {e}")
        return jsonify({"error": "Internal server error during login."}), 500


# ── GET/POST /logout ─────────────────────────────────────────
@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    logger.info("[Auth] User logged out.")
    if request.method == "GET":
        from flask import redirect, url_for
        return redirect(url_for("views.login_page"))
    return jsonify({"status": "success", "message": "Logout successful."}), 200


# ── POST /verify ─────────────────────────────────────────────
@auth_bp.route("/verify", methods=["POST"])
def verify_doctor():
    try:
        if session.get("role") != "admin":
            return jsonify({"error": "Unauthorized. Super Admin access required."}), 403

        data = request.get_json(force=True, silent=True) or {}
        doctor_id = data.get("doctor_id")
        action = data.get("action")

        if not doctor_id or action not in ["approve", "reject"]:
            return jsonify({"error": "Invalid doctor ID or verification action."}), 400

        doctor = User.query.get(doctor_id)
        if not doctor or doctor.role != "doctor":
            return jsonify({"error": "Doctor account not found."}), 404

        doctor.status = "approved" if action == "approve" else "rejected"
        db.session.commit()

        logger.info(f"[Auth] Admin {session.get('user_id')} updated Doctor {doctor.email} status to: {doctor.status}")
        return jsonify({
            "status": "success",
            "message": f"Doctor status successfully updated to {doctor.status}.",
            "doctor": {"id": doctor.id, "email": doctor.email, "status": doctor.status},
        }), 200

    except Exception as e:
        logger.exception(f"[Auth] Error during doctor verification: {e}")
        return jsonify({"error": "Internal server error during verification."}), 500


# ── POST /reupload ───────────────────────────────────────────
@auth_bp.route("/reupload", methods=["POST"])
def reupload_proof():
    """Allow rejected doctors to re-submit credentials."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    user = User.query.get(user_id)
    if not user or user.role != "doctor":
        return jsonify({"error": "Doctor account not found."}), 404

    if user.status not in ("rejected", "pending"):
        return jsonify({"error": "Credential re-upload is only available for rejected accounts."}), 400

    if "proof" not in request.files:
        return jsonify({"error": "Proof document is required."}), 400

    file = request.files["proof"]
    if file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file format."}), 400

    filename = secure_filename(file.filename)
    unique_filename = f"{int(time.time())}_{filename}"
    upload_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_filename)
    file.save(upload_path)

    user.proof_filename = unique_filename
    user.status = "pending"
    db.session.commit()
    session["status"] = "pending"

    return jsonify({
        "status": "success",
        "message": "Credentials re-submitted. Your account is pending verification.",
    }), 200


# ── POST /users/manage ───────────────────────────────────────
@auth_bp.route("/users/manage", methods=["POST"])
def manage_user():
    """Super Admin: update user role or status."""
    if session.get("role") != "admin":
        return jsonify({"error": "Unauthorized."}), 403

    data = request.get_json(force=True, silent=True) or {}
    target_id = data.get("user_id")
    new_status = data.get("status")
    new_role = data.get("role")

    if not target_id:
        return jsonify({"error": "User ID required."}), 400

    user = User.query.get(target_id)
    if not user:
        return jsonify({"error": "User not found."}), 404

    if user.id == session.get("user_id"):
        return jsonify({"error": "Cannot modify your own account."}), 400

    if new_status in ("approved", "pending", "rejected"):
        user.status = new_status
    if new_role in ("doctor", "patient", "admin"):
        user.role = new_role

    db.session.commit()
    return jsonify({
        "status": "success",
        "user": {"id": user.id, "email": user.email, "role": user.role, "status": user.status},
    }), 200
