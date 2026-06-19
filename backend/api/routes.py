"""
Smart Health Sync — API Routes (RESTful endpoints)
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026
"""

import json
import logging
from flask import Blueprint, request, jsonify, session

from backend.database.models import db, DiagnosticRecord
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

        model_key = str(data.get("model", "random_forest"))
        patient_ref = str(data.get("patient_reference", "")).strip() or None
        linked_patient_id = data.get("patient_id")
        result    = model_manager.predict(features_dict, model_key)

        user_id = session.get("user_id")
        if user_id:
            try:
                record = DiagnosticRecord(
                    user_id=user_id,
                    patient_reference=patient_ref,
                    biomarkers_json=json.dumps(features_dict),
                    result_json=json.dumps(result),
                    prediction_label=result["prediction"],
                    confidence_score=result["confidence"],
                    model_version=result.get("model_used"),
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
    elif role == "doctor" and record.user_id == user_id:
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
