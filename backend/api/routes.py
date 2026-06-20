"""
Smart Health Sync — API Routes (RESTful endpoints)
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026
"""

import json
import logging
from flask import Blueprint, request, jsonify, session, current_app

from backend.database.models import db, DiagnosticRecord, User, Patient, DoctorPatientConnection, DoctorTechnicianConnection
from backend.ml.model_manager import model_manager

logger  = logging.getLogger("smarthealth.api")
api_bp  = Blueprint("api", __name__)


# ── /api/health ──────────────────────────────────────────────
@api_bp.route("/health", methods=["GET"])
def health():
    """General system health check."""
    return jsonify({
        "status":  "online",
        "service": "Smart Health Sync API",
        "version": "2.0.0",
    }), 200


# ── /api/health/models ───────────────────────────────────────
@api_bp.route("/health/models", methods=["GET"])
def health_models():
    """
    Detailed ML model health status.

    Returns:
        JSON with loaded/missing/corrupted model lists and directory info.
    """
    report = model_manager.health_report()
    status_code = 200 if report["loaded_models"] else 503
    return jsonify(report), status_code


# ── /api/predict ─────────────────────────────────────────────
@api_bp.route("/predict", methods=["POST"])
def predict():
    """
    Clinical diagnostic inference endpoint.

    Accepts:
        POST JSON body:
        {
            "features": {
                "Glucose": 0.72,
                "Cholesterol": 0.45,
                ... (24 biomarkers)
            },
            "model": "random_forest"  (optional)
        }

    Returns:
        Structured prediction with confidence, probabilities, and recommendations.
    """
    try:
        # Check permissions: must be verified doctor or admin
        role = session.get("role")
        status = session.get("status")
        if role != "admin" and (role != "doctor" or status != "approved"):
            return jsonify({
                "error": "Access denied. Diagnostic features require a verified doctor account.",
                "status": "failed"
            }), 403

        data = request.get_json(force=True, silent=True)
        if not data:
            return jsonify({
                "error":  "Missing or malformed JSON body.",
                "status": "failed",
            }), 400

        features_dict = data.get("features")
        if features_dict is None:
            return jsonify({
                "error":   "Missing 'features' key in request body.",
                "example": {
                    "features": {f: 0.5 for f in model_manager.features[:3]},
                    "model": "random_forest",
                },
                "status": "failed",
            }), 400

        if not isinstance(features_dict, dict):
            return jsonify({
                "error":  "'features' must be a JSON object (dict).",
                "status": "failed",
            }), 400

        # Validate biomarker ranges:
        for f_name, f_val in features_dict.items():
            try:
                val_f = float(f_val)
                if val_f < 0.0 or val_f > 1.0:
                    return jsonify({
                        "error": f"Biomarker '{f_name}' value {f_val} is out of bounds (must be between 0.0 and 1.0).",
                        "status": "failed"
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    "error": f"Biomarker '{f_name}' must be a numeric value.",
                    "status": "failed"
                }), 400

        model_key = str(data.get("model", "random_forest"))
        patient_ref = str(data.get("patient_reference", "")).strip() or None
        linked_patient_id = data.get("patient_id")

        if linked_patient_id:
            from backend.database.models import Patient
            patient = Patient.query.get(int(linked_patient_id))
            if patient:
                if not patient_ref or patient_ref.startswith("[Auto") or patient_ref.strip() == f"{patient.first_name} {patient.last_name}":
                    import random
                    rand_suffix = "".join(random.choices("0123456789ABCDEF", k=6))
                    patient_ref = f"SHS-{patient.first_name[0].upper()}{patient.last_name[0].upper()}-{rand_suffix}"
        elif not patient_ref:
            import random
            rand_suffix = "".join(random.choices("0123456789ABCDEF", k=6))
            patient_ref = f"SHS-GEN-{rand_suffix}"

        result    = model_manager.predict(features_dict, model_key)

        user_id = session.get("user_id")
        if user_id:
            try:
                draft_id = data.get("draft_id") or data.get("record_id")
                record = None
                if draft_id and role in ("doctor", "admin"):
                    record = DiagnosticRecord.query.filter_by(id=int(draft_id), user_id=user_id, status="draft").first()
                
                if record:
                    record.biomarkers_json = json.dumps(features_dict)
                    record.result_json = json.dumps(result)
                    record.prediction_label = result["prediction"]
                    record.confidence_score = result["confidence"]
                    record.model_version = result.get("model_used")
                    record.status = "approved"
                else:
                    status_val = "approved" if role in ("doctor", "admin") else ("draft" if linked_patient_id else "approved")
                    record = DiagnosticRecord(
                        user_id=user_id,
                        patient_reference=patient_ref,
                        biomarkers_json=json.dumps(features_dict),
                        result_json=json.dumps(result),
                        prediction_label=result["prediction"],
                        confidence_score=result["confidence"],
                        model_version=result.get("model_used"),
                        status=status_val,
                    )
                    if linked_patient_id is not None:
                        from backend.database.models import Patient
                        patient = Patient.query.get(int(linked_patient_id))
                        if patient:
                            record.patient_id = patient.id
                    db.session.add(record)
                db.session.commit()
                result["record_id"] = record.id
            except Exception as db_exc:
                db.session.rollback()
                logger.warning(f"[API] Could not persist diagnostic record: {db_exc}")

        logger.info(
            f"[API] Prediction: {result['prediction']} | "
            f"confidence={result['confidence']}% | model={result['model_used']}"
        )
        return jsonify(result), 200

    except ValueError as ve:
        logger.warning(f"[API] Validation error: {ve}")
        return jsonify({
            "error":  str(ve),
            "status": "failed",
            "available_features": model_manager.features,
        }), 400

    except RuntimeError as re:
        logger.error(f"[API] Model runtime error: {re}")
        return jsonify({
            "error":  "Diagnostic models not available.",
            "details": {
                "message":         str(re),
                "missing_models":  model_manager.missing_models,
                "corrupted_models":model_manager.corrupted_models,
                "models_directory":str(model_manager.models_dir),
            },
            "status": "failed",
        }), 503

    except Exception as exc:
        logger.exception(f"[API] Unexpected error during prediction: {exc}")
        return jsonify({
            "error":  "Internal server error.",
            "status": "failed",
        }), 500


# ── /api/history ─────────────────────────────────────────────
@api_bp.route("/history", methods=["GET"])
def diagnosis_history():
    """Return diagnosis history for the logged-in user (or all for admin)."""
    user_id = session.get("user_id")
    role = session.get("role")
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    if role == "admin":
        records = DiagnosticRecord.query.order_by(DiagnosticRecord.created_at.desc()).limit(100).all()
    elif role == "doctor" and session.get("status") == "approved":
        records = (
            DiagnosticRecord.query.filter_by(user_id=user_id)
            .order_by(DiagnosticRecord.created_at.desc())
            .limit(100)
            .all()
        )
    elif role == "patient":
        from backend.database.models import Patient
        profile = Patient.query.filter_by(user_id=user_id).first()
        if not profile:
            records = []
        else:
            records = (
                DiagnosticRecord.query.filter_by(patient_id=profile.id)
                .order_by(DiagnosticRecord.created_at.desc())
                .limit(100)
                .all()
            )
    else:
        return jsonify({"error": "Access denied."}), 403

    return jsonify({
        "status": "success",
        "records": [r.to_dict() for r in records],
    }), 200


# ── /api/history/<id> ────────────────────────────────────────
@api_bp.route("/history/<int:record_id>", methods=["GET"])
def diagnosis_record(record_id):
    """Return a single diagnosis record."""
    user_id = session.get("user_id")
    role = session.get("role")
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401

    record = DiagnosticRecord.query.get(record_id)
    if not record:
        return jsonify({"error": "Record not found."}), 404

    if role == "admin":
        pass
    elif role == "doctor" and int(record.user_id) == int(user_id):
        pass
    elif role == "patient":
        from backend.database.models import Patient
        profile = Patient.query.filter_by(user_id=user_id).first()
        if not profile or record.patient_id != profile.id:
            return jsonify({"error": "Access denied."}), 403
    else:
        return jsonify({"error": "Access denied."}), 403

    return jsonify({"status": "success", "record": record.to_dict()}), 200


# ── /api/models ──────────────────────────────────────────────
@api_bp.route("/models", methods=["GET"])
def list_models():
    """Return metadata about available ML classifiers."""
    return jsonify({
        "available_models": list(model_manager.loaded_models.keys()),
        "default_model":    "random_forest",
        "features":         model_manager.features,
        "classes":          model_manager.classes,
        "model_metadata":   _build_metadata(),
    }), 200


# ── /api/metadata ────────────────────────────────────────────
@api_bp.route("/metadata", methods=["GET"])
def metadata():
    """API metadata root."""
    return jsonify({
        "project":   "Smart Health Sync",
        "version":   "2.0.0",
        "developer": {
            "names":       "Enock Queenson Eduafo & Christabel Araba Edumadze",
            "student_ids": "11014444 & 11348914",
            "institution": "University of Ghana",
            "supervisor":  "Professor Solomon Mensah",
            "year":        "2026",
        },
        "endpoints": {
            "/api/health":        "GET  — System health check",
            "/api/health/models": "GET  — ML model health report",
            "/api/predict":       "POST — Clinical diagnostic inference",
            "/api/history":       "GET  — Diagnosis history",
            "/api/models":        "GET  — Available classifiers",
        },
        "supported_conditions": model_manager.classes,
    }), 200


# ── Helpers ──────────────────────────────────────────────────
def _build_metadata() -> dict:
    """Build classifier metadata from results_summary if available."""
    base = {
        "random_forest":       {"accuracy": 0.9507, "framework": "scikit-learn", "status": "production"},
        "svm":                 {"accuracy": 0.9489, "framework": "scikit-learn", "status": "valid"},
        "decision_tree":       {"accuracy": 0.9261, "framework": "scikit-learn", "status": "valid"},
        "logistic_regression": {"accuracy": 0.8187, "framework": "scikit-learn", "status": "baseline"},
    }
    if model_manager.summary:
        for m in model_manager.summary.get("models", []):
            key = m.get("name", "").lower().replace(" ", "_")
            key_map = {
                "random_forest": "random_forest",
                "support_vector_machine": "svm",
                "decision_tree": "decision_tree",
                "logistic_regression": "logistic_regression",
            }
            mapped = key_map.get(key)
            if mapped:
                base[mapped].update({
                    "accuracy":  m.get("accuracy"),
                    "precision": m.get("precision"),
                    "recall":    m.get("recall"),
                    "f1_score":  m.get("f1_score"),
                    "cv_mean":   m.get("cv_mean"),
                })
    return base





# ── POST /history/<id>/explain ───────────────────────────────
@api_bp.route("/history/<int:record_id>/explain", methods=["POST"])
def explain_diagnosis(record_id):
    """Call Groq API to answer patient questions about a diagnosis report."""
    import os
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
        
    record = DiagnosticRecord.query.get(record_id)
    if not record:
        return jsonify({"error": "Diagnosis record not found."}), 404
        
    # Security check: only the linked patient, diagnosing doctor, or admin can query
    role = session.get("role")
    if role == "patient":
        from backend.database.models import Patient
        profile = Patient.query.filter_by(user_id=user_id).first()
        if not profile or record.patient_id != profile.id:
            return jsonify({"error": "Access denied."}), 403
        if record.status != "approved":
            return jsonify({"error": "Access denied. Diagnosis is not finalized."}), 403
    elif role == "doctor":
        if int(record.user_id) != int(user_id):
            return jsonify({"error": "Access denied."}), 403
    elif role != "admin":
        return jsonify({"error": "Access denied."}), 403
        
    data = request.get_json(force=True, silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required."}), 400
        
    groq_api_key = current_app.config.get("GROQ_API_KEY") or os.environ.get("GROQ_API_KEY")
    if not groq_api_key:
        return jsonify({
            "status": "error",
            "reply": "The AI explainer assistant is currently offline (missing configuration). Please consult your healthcare provider directly for any questions."
        }), 200
        
    try:
        import json
        
        # Format biomarker data for context
        biomarkers = json.loads(record.biomarkers_json) if record.biomarkers_json else {}
        biomarkers_list = []
        for k, v in biomarkers.items():
            biomarkers_list.append(f"- {k}: {v:.2f}")
        biomarkers_text = "\n".join(biomarkers_list)
        
        system_prompt = (
            "You are an empathetic, clear, and professional clinical explanation assistant for Smart Health Sync.\n"
            "Explain the patient's diagnosis report context clearly and answer their questions simply. Use clear language and bullet points.\n"
            "Explain what each high/low biomarker indicates related to their condition.\n"
            "IMPORTANT: Always include a short disclaimer that you are an academic AI assistant prototype and they should verify details with their doctor.\n\n"
            f"REPORT DETAILS:\n"
            f"Predicted Condition: {record.prediction_label}\n"
            f"AI Confidence: {record.confidence_score:.1f}%\n"
            f"Doctor's Remarks: {record.doctor_remarks or 'No remarks added by doctor yet.'}\n\n"
            f"BIOMARKER LEVEL SCORES (normalised 0.0 to 1.0):\n"
            f"{biomarkers_text}"
        )
        
        try:
            from groq import Groq
            client = Groq(api_key=groq_api_key)
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                temperature=0.5,
                max_tokens=800
            )
            reply = completion.choices[0].message.content
            return jsonify({"status": "success", "reply": reply}), 200
        except ImportError:
            # Fallback to standard requests if SDK is not installed
            import requests
            headers = {
                "Authorization": f"Bearer {groq_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": message}
                ],
                "temperature": 0.5,
                "max_tokens": 800
            }
            res = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=15)
            if res.status_code != 200:
                logger.warning(f"Groq API returned status {res.status_code}: {res.text}")
                return jsonify({
                    "status": "error",
                    "reply": "The AI explainer is temporarily busy. Please try again shortly or speak with your doctor."
                }), 200
                
            res_data = res.json()
            reply = res_data["choices"][0]["message"]["content"]
            return jsonify({"status": "success", "reply": reply}), 200
            
    except Exception as e:
        logger.exception(f"Error calling Groq API: {e}")
        return jsonify({
            "status": "error",
            "reply": "An error occurred while calling the AI model. Please speak to your doctor."
        }), 200


# ── POST /history/<id>/approve ───────────────────────────────
@api_bp.route("/history/<int:record_id>/approve", methods=["POST"])
def approve_diagnosis(record_id):
    """Doctor approves a diagnosis draft, adding remarks and updating status."""
    user_id = session.get("user_id")
    role = session.get("role")
    
    if not user_id or role not in ("doctor", "admin"):
        return jsonify({"error": "Access denied. Doctor account required."}), 403
        
    record = DiagnosticRecord.query.get(record_id)
    if not record:
        return jsonify({"error": "Diagnosis record not found."}), 404
        
    if role == "doctor" and int(record.user_id) != int(user_id):
        return jsonify({"error": "Access denied. You can only sign off on your own diagnoses."}), 403
        
    data = request.get_json(force=True, silent=True) or {}
    remarks = data.get("remarks", "").strip()
    model_key = data.get("model", "random_forest")
    
    try:
        biomarkers = json.loads(record.biomarkers_json) if record.biomarkers_json else {}
        result = model_manager.predict(biomarkers, model_key)
        record.prediction_label = result["prediction"]
        record.confidence_score = result["confidence"]
        record.model_version = result.get("model_used")
        record.result_json = json.dumps(result)
    except Exception as exc:
        logger.warning(f"Error running model {model_key} on draft: {exc}")
        
    record.doctor_remarks = remarks or None
    record.status = "approved"
    db.session.commit()
    
    logger.info(f"[API] Doctor {user_id} approved record {record_id} with remarks.")
    return jsonify({
        "status": "success",
        "message": "Diagnosis successfully approved and shared with patient.",
        "record": record.to_dict()
    }), 200


# ── POST /api/technician/connect ────────────────────────────
@api_bp.route("/technician/connect", methods=["POST"])
def technician_connect_doctor():
    user_id = session.get("user_id")
    role = session.get("role")
    if not user_id or role != "technician":
        return jsonify({"error": "Unauthorized. Technician access required."}), 403
    data = request.get_json(force=True, silent=True) or {}
    doctor_id = data.get("doctor_id")
    if not doctor_id:
        return jsonify({"error": "Doctor ID is required."}), 400
    doctor = User.query.filter_by(id=doctor_id, role="doctor", status="approved").first()
    if not doctor:
        return jsonify({"error": "Verified doctor not found."}), 404
    from backend.database.models import DoctorTechnicianConnection
    existing = DoctorTechnicianConnection.query.filter_by(doctor_id=doctor.id, technician_id=user_id).first()
    if existing:
        if existing.status == "rejected":
            existing.status = "pending"
            existing.created_at = datetime.utcnow()
            db.session.commit()
            return jsonify({"status": "success", "message": "Connection request re-submitted."}), 200
        return jsonify({"error": f"Connection request is already {existing.status}."}), 400
    connection = DoctorTechnicianConnection(doctor_id=doctor.id, technician_id=user_id, status="pending")
    db.session.add(connection)
    db.session.commit()
    return jsonify({"status": "success", "message": "Connection request sent successfully."}), 201


# ── POST /api/doctor/respond-technician ──────────────────────
@api_bp.route("/doctor/respond-technician", methods=["POST"])
def doctor_respond_technician():
    user_id = session.get("user_id")
    role = session.get("role")
    if not user_id or role != "doctor":
        return jsonify({"error": "Unauthorized. Doctor access required."}), 403
    data = request.get_json(force=True, silent=True) or {}
    connection_id = data.get("connection_id")
    action = data.get("action")  # approve or reject
    if not connection_id or action not in ("approve", "reject"):
        return jsonify({"error": "Connection ID and valid action (approve/reject) are required."}), 400
    from backend.database.models import DoctorTechnicianConnection
    connection = DoctorTechnicianConnection.query.filter_by(id=connection_id, doctor_id=user_id).first()
    if not connection:
        return jsonify({"error": "Connection request not found."}), 404
    connection.status = "approved" if action == "approve" else "rejected"
    db.session.commit()
    return jsonify({
        "status": "success",
        "message": f"Connection successfully {connection.status}d.",
        "connection": {"id": connection.id, "status": connection.status}
    }), 200


# ── GET /api/doctor/<id>/patients ────────────────────────────
@api_bp.route("/doctor/<int:doctor_id>/patients", methods=["GET"])
def doctor_patients(doctor_id):
    user_id = session.get("user_id")
    role = session.get("role")
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
    
    if role == "technician":
        from backend.database.models import DoctorTechnicianConnection
        conn = DoctorTechnicianConnection.query.filter_by(doctor_id=doctor_id, technician_id=user_id, status="approved").first()
        if not conn:
            return jsonify({"error": "Access denied. You are not an approved technician for this doctor."}), 403
    elif role == "doctor" and int(user_id) == int(doctor_id):
        pass
    elif role == "admin":
        pass
    else:
        return jsonify({"error": "Access denied."}), 403
        
    from backend.database.models import DoctorPatientConnection
    connections = DoctorPatientConnection.query.filter_by(doctor_id=doctor_id, status="approved").all()
    patients_list = []
    for conn in connections:
        p = conn.patient
        patients_list.append({
            "id": p.id,
            "first_name": p.first_name,
            "last_name": p.last_name,
            "email": p.user.email if p.user else "",
            "patient_uuid": p.patient_uuid
        })
    return jsonify({"status": "success", "patients": patients_list}), 200


# ── POST /api/technician/submit-biomarkers ───────────────────
@api_bp.route("/technician/submit-biomarkers", methods=["POST"])
def technician_submit_biomarkers():
    user_id = session.get("user_id")
    role = session.get("role")
    if not user_id or role != "technician":
        return jsonify({"error": "Unauthorized. Technician access required."}), 403
    data = request.get_json(force=True, silent=True) or {}
    doctor_id = data.get("doctor_id")
    patient_id = data.get("patient_id")
    features = data.get("features")
    patient_ref = data.get("patient_reference", "").strip() or None
    
    if not doctor_id or not patient_id or not features:
        return jsonify({"error": "Doctor ID, Patient ID, and Biomarkers features are required."}), 400

    if not isinstance(features, dict):
        return jsonify({"error": "Biomarkers features must be a JSON object (dict)."}), 400

    # Validate biomarker ranges:
    for f_name, f_val in features.items():
        try:
            val_f = float(f_val)
            if val_f < 0.0 or val_f > 1.0:
                return jsonify({
                    "error": f"Biomarker '{f_name}' value {f_val} is out of bounds (must be between 0.0 and 1.0)."
                }), 400
        except (ValueError, TypeError):
            return jsonify({
                "error": f"Biomarker '{f_name}' must be a numeric value."
            }), 400
        
    from backend.database.models import DoctorTechnicianConnection, Patient
    conn = DoctorTechnicianConnection.query.filter_by(doctor_id=doctor_id, technician_id=user_id, status="approved").first()
    if not conn:
        return jsonify({"error": "Access denied. You are not approved by this doctor."}), 403
        
    patient = Patient.query.get(int(patient_id))
    if not patient:
        return jsonify({"error": "Patient not found."}), 404
        
    if not patient_ref:
        import random
        rand_suffix = "".join(random.choices("0123456789ABCDEF", k=6))
        patient_ref = f"SHS-{patient.first_name[0].upper()}{patient.last_name[0].upper()}-{rand_suffix}"
        
    try:
        result = model_manager.predict(features, "random_forest")
    except Exception as exc:
        return jsonify({"error": f"Model inference error: {str(exc)}"}), 500
        
    record = DiagnosticRecord(
        user_id=doctor_id,
        patient_id=patient.id,
        patient_reference=patient_ref,
        biomarkers_json=json.dumps(features),
        result_json=json.dumps(result),
        prediction_label=result["prediction"],
        confidence_score=result["confidence"],
        model_version=result.get("model_used"),
        status="draft",
    )
    db.session.add(record)
    db.session.commit()
    
    return jsonify({"status": "success", "message": "Biomarkers submitted as draft successfully.", "record_id": record.id}), 201


# ── GET /api/history/<id>/preview-models ──────────────────────
@api_bp.route("/history/<int:record_id>/preview-models", methods=["GET"])
def preview_models(record_id):
    user_id = session.get("user_id")
    role = session.get("role")
    if not user_id:
        return jsonify({"error": "Authentication required."}), 401
        
    record = DiagnosticRecord.query.get(record_id)
    if not record:
        return jsonify({"error": "Record not found."}), 404
        
    if role == "doctor" and int(record.user_id) != int(user_id):
        return jsonify({"error": "Access denied."}), 403
    elif role == "technician":
        from backend.database.models import DoctorTechnicianConnection
        conn = DoctorTechnicianConnection.query.filter_by(doctor_id=record.user_id, technician_id=user_id, status="approved").first()
        if not conn:
            return jsonify({"error": "Access denied."}), 403
    elif role != "admin":
        return jsonify({"error": "Access denied."}), 403
        
    biomarkers = json.loads(record.biomarkers_json) if record.biomarkers_json else {}
    predictions = {}
    for model_key in ["random_forest", "svm", "decision_tree", "logistic_regression"]:
        try:
            res = model_manager.predict(biomarkers, model_key)
            predictions[model_key] = {
                "prediction": res["prediction"],
                "confidence": res["confidence"],
                "probabilities": res.get("probabilities", {})
            }
        except Exception as exc:
            predictions[model_key] = {"error": str(exc)}
            
    return jsonify({"status": "success", "predictions": predictions}), 200


# ── GET /api/doctor/patient/<int:patient_id>/drafts ──────────
@api_bp.route("/doctor/patient/<int:patient_id>/drafts", methods=["GET"])
def get_patient_drafts(patient_id):
    user_id = session.get("user_id")
    role = session.get("role")
    if not user_id or role != "doctor":
        return jsonify({"error": "Unauthorized. Doctor access required."}), 403
        
    drafts = DiagnosticRecord.query.filter_by(
        user_id=user_id,
        patient_id=patient_id,
        status="draft"
    ).order_by(DiagnosticRecord.created_at.desc()).all()
    
    return jsonify({
        "status": "success",
        "drafts": [{
            "id": d.id,
            "patient_reference": d.patient_reference,
            "created_at": d.created_at.strftime('%d %b %Y, %H:%M') if d.created_at else '',
            "biomarkers": json.loads(d.biomarkers_json) if d.biomarkers_json else {}
        } for d in drafts]
    }), 200

