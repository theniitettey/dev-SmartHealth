"""
Smart Health Sync — Professional Model Manager
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026

Handles model discovery, loading, validation, caching, and inference
with robust path resolution for local and cloud environments.
"""

import os
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

import joblib
import numpy as np

# ─── Logger ──────────────────────────────────────────────────
logger = logging.getLogger("smarthealth.ml")

# ─── Constants ───────────────────────────────────────────────
# Feature order MUST match train_models.py StandardScaler fit
FEATURE_ORDER = [
    "Glucose", "Cholesterol", "Hemoglobin", "Platelets",
    "White Blood Cells", "Red Blood Cells", "Hematocrit",
    "Mean Corpuscular Volume", "Mean Corpuscular Hemoglobin",
    "Mean Corpuscular Hemoglobin Concentration", "Insulin", "BMI",
    "Systolic Blood Pressure", "Diastolic Blood Pressure", "Triglycerides",
    "HbA1c", "LDL Cholesterol", "HDL Cholesterol", "ALT", "AST",
    "Heart Rate", "Creatinine", "Troponin", "C-reactive Protein",
]

CLASS_LABELS = [
    "Anemia", "Diabetes", "Healthy", "Heart Disease",
    "Thalassemia", "Thrombocytopenia",
]

CLASS_DESCRIPTIONS = {
    "Healthy":          "Physiological markers within established clinical baseline ranges.",
    "Diabetes":         "Glucose and HbA1c elevation suggests chronic metabolic dysregulation.",
    "Anemia":           "Red blood cell counts or haemoglobin concentration below physiological norms.",
    "Heart Disease":    "Cardiovascular enzyme and lipid markers indicate cardiac stress.",
    "Thalassemia":      "Hereditary blood disorder affecting haemoglobin production pathways.",
    "Thrombocytopenia": "Low platelet count indicating critical clotting risk factors.",
}

CLASS_RECOMMENDATIONS = {
    "Healthy":          ["Maintain your current healthy lifestyle and regular check-ups."],
    "Diabetes":         [
        "Consult an endocrinologist for HbA1c management.",
        "Monitor blood glucose levels regularly.",
        "Follow a low-glycaemic diet plan.",
    ],
    "Anemia":           [
        "Consult a haematologist for iron studies.",
        "Consider dietary iron supplementation.",
        "Follow up with full blood count in 4–6 weeks.",
    ],
    "Heart Disease":    [
        "Seek immediate cardiology review.",
        "Monitor lipid panel and troponin levels.",
        "Avoid high-sodium, high-fat diets.",
    ],
    "Thalassemia":      [
        "Genetic counselling is recommended.",
        "Regular haematology follow-up required.",
        "Avoid iron supplements without specialist advice.",
    ],
    "Thrombocytopenia": [
        "Urgent haematology consultation advised.",
        "Avoid aspirin and NSAIDs.",
        "Monitor for bleeding symptoms.",
    ],
}

GENERIC_RECOMMENDATIONS = [
    "Consult a licensed medical professional for formal clinical review.",
    "Ensure all biomarker inputs match your latest laboratory report.",
    "Do not modify any ongoing treatment based exclusively on algorithmic predictions.",
]


# ─── Path Resolution ─────────────────────────────────────────
def resolve_models_dir() -> Path:
    """
    Locate the /models directory across all common deployment environments.
    Supports: local dev, Render, Railway, Docker (/app), Vercel (/var/task).

    Preference order:
      1. MODEL_STORAGE_PATH env var
      2. Root-level /models (most common local + deployment layout)
      3. /app/models (Docker generic)
      4. /var/task/models (Vercel)
    """
    # 1. Environment variable override
    env_path = os.environ.get("MODEL_STORAGE_PATH", "")
    if env_path and Path(env_path).exists():
        logger.info(f"[ModelManager] Using MODEL_STORAGE_PATH: {env_path}")
        return Path(env_path)

    # 2. Walk up from this file to repo root, then check /models
    here = Path(__file__).resolve()
    candidate_roots = [
        here.parent.parent.parent,   # backend/ml/model_manager.py -> 3 levels up = repo root
        here.parent.parent,          # 2 levels up
        Path("/app"),                # Render / Railway / Docker
        Path("/var/task"),           # Vercel
        Path(os.getcwd()),           # Current working directory
    ]
    for root in candidate_roots:
        candidate = root / "models"
        if candidate.exists() and candidate.is_dir():
            # Prefer directories that actually contain .pkl files
            has_pkl = any(candidate.glob("*.pkl"))
            if has_pkl:
                logger.info(f"[ModelManager] Models directory (with .pkl): {candidate}")
                return candidate

    # 3. Fallback: return any existing models dir even without .pkl
    for root in candidate_roots:
        candidate = root / "models"
        if candidate.exists() and candidate.is_dir():
            logger.info(f"[ModelManager] Models directory (empty): {candidate}")
            return candidate

    # 4. Last resort: best guess
    fallback = here.parent.parent.parent / "models"
    logger.warning(f"[ModelManager] Could not locate models dir, defaulting to: {fallback}")
    return fallback


# ─── ModelManager ────────────────────────────────────────────
class ModelManager:
    """
    Singleton model manager that handles:
    - Multi-path model discovery
    - Safe loading with integrity checks
    - In-memory caching
    - Startup validation
    - Prediction inference
    """

    _instance: Optional["ModelManager"] = None

    def __new__(cls) -> "ModelManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialised = False
        return cls._instance

    def __init__(self):
        if self._initialised:
            return
        self._initialised = True

        self.models_dir:     Path             = resolve_models_dir()
        self.loaded_models:  Dict[str, Any]   = {}
        self.missing_models: list             = []
        self.corrupted_models: list           = []
        self.scaler:         Optional[Any]    = None
        self.label_encoder:  Optional[Any]    = None
        self.summary:        Optional[dict]   = None
        self.features:       list             = FEATURE_ORDER
        self.classes:        list             = CLASS_LABELS

        self._run_startup_validation()

    # ── Startup ──────────────────────────────────────────────
    def _run_startup_validation(self):
        """Load all required artefacts at startup and log status."""
        logger.info("=" * 60)
        logger.info("[SmartHealth] Starting ML model validation …")
        logger.info(f"[SmartHealth] Models directory: {self.models_dir}")
        logger.info(f"[SmartHealth] Directory exists: {self.models_dir.exists()}")

        if self.models_dir.exists():
            found = list(self.models_dir.iterdir())
            logger.info(f"[SmartHealth] Files found ({len(found)}): "
                        f"{[f.name for f in found]}")
        else:
            logger.warning("[SmartHealth] Models directory NOT found!")

        # Load preprocessing
        self._load_artefact("scaler",        "scaler.pkl",        kind="scaler")
        self._load_artefact("label_encoder", "label_encoder.pkl", kind="encoder")
        self._load_summary()

        # Load classifiers
        classifier_map = {
            "random_forest":      "random_forest.pkl",
            "svm":                "support_vector_machine.pkl",
            "decision_tree":      "decision_tree.pkl",
            "logistic_regression":"logistic_regression.pkl",
        }
        for key, filename in classifier_map.items():
            self._load_model(key, filename)

        # Summary log
        logger.info(f"[SmartHealth] ✓ Loaded models : {list(self.loaded_models.keys())}")
        logger.info(f"[SmartHealth] ✗ Missing models: {self.missing_models}")
        logger.info(f"[SmartHealth] ✗ Corrupt models: {self.corrupted_models}")
        logger.info("=" * 60)

    def _load_artefact(self, attr_name: str, filename: str, kind: str):
        path = self.models_dir / filename
        if not path.exists():
            logger.warning(f"[SmartHealth] Missing {kind}: {filename}")
            self.missing_models.append(filename)
            return
        try:
            obj = joblib.load(path)
            setattr(self, attr_name, obj)
            logger.info(f"[SmartHealth] Loaded {kind}: {filename}")
        except Exception as exc:
            logger.error(f"[SmartHealth] Corrupted {kind}: {filename} — {exc}", exc_info=True)
            self.corrupted_models.append(filename)

    def _load_summary(self):
        path = self.models_dir / "results_summary.json"
        if not path.exists():
            logger.warning("[SmartHealth] results_summary.json not found — using defaults.")
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                self.summary = json.load(fh)
            if self.summary.get("features"):
                self.features = self.summary["features"]
            if self.summary.get("classes"):
                self.classes  = self.summary["classes"]
            logger.info("[SmartHealth] Loaded results_summary.json")
        except Exception as exc:
            logger.error(f"[SmartHealth] Failed to read results_summary.json: {exc}")
            self.corrupted_models.append("results_summary.json")

    def _load_model(self, key: str, filename: str):
        path = self.models_dir / filename
        if not path.exists():
            logger.warning(f"[SmartHealth] Missing model: {filename}")
            self.missing_models.append(filename)
            return
        try:
            model = joblib.load(path)
            self.loaded_models[key] = model
            logger.info(f"[SmartHealth] ✓ Loaded model: {key} ({filename})")
        except Exception as exc:
            logger.error(f"[SmartHealth] ✗ Corrupted model: {filename} — {exc}", exc_info=True)
            self.corrupted_models.append(filename)

    # ── Health Check ─────────────────────────────────────────
    def health_report(self) -> dict:
        """Return structured health status for the /api/health/models endpoint."""
        return {
            "status":           "healthy" if self.loaded_models else "degraded",
            "models_directory": str(self.models_dir),
            "directory_exists": self.models_dir.exists(),
            "loaded_models":    list(self.loaded_models.keys()),
            "missing_models":   self.missing_models,
            "corrupted_models": self.corrupted_models,
            "scaler_loaded":    self.scaler is not None,
            "encoder_loaded":   self.label_encoder is not None,
            "feature_count":    len(self.features),
        }

    # ── Inference ────────────────────────────────────────────
    def predict(self, features_dict: dict, model_key: str = "random_forest") -> dict:
        """
        Run inference on a features dictionary.

        Args:
            features_dict: {feature_name: float_value}
            model_key: one of random_forest | svm | decision_tree | logistic_regression

        Returns:
            Structured prediction result dict.

        Raises:
            RuntimeError if no model is available.
            ValueError on missing / invalid features.
        """
        # ── Validate model availability ──────────────────────
        model_key = self._normalise_key(model_key)
        model = self.loaded_models.get(model_key)
        fallback_used = False

        if model is None:
            # Try fallback cascade
            for fallback in ["random_forest", "svm", "decision_tree", "logistic_regression"]:
                if self.loaded_models.get(fallback):
                    model = self.loaded_models[fallback]
                    model_key = fallback
                    fallback_used = True
                    logger.warning(f"[SmartHealth] Fallback to model: {fallback}")
                    break

        if model is None:
            raise RuntimeError(
                "No diagnostic models are currently loaded. "
                f"Missing: {self.missing_models}, Corrupted: {self.corrupted_models}"
            )

        # ── Validate features ────────────────────────────────
        missing_features = [f for f in self.features if f not in features_dict]
        if missing_features:
            raise ValueError(f"Missing biomarker inputs: {missing_features}")

        try:
            X_raw = np.array(
                [float(features_dict[f]) for f in self.features],
                dtype=np.float64,
            ).reshape(1, -1)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Invalid numeric value in features: {exc}") from exc

        # ── Preprocess ───────────────────────────────────────
        X = X_raw
        if self.scaler is not None:
            X = self.scaler.transform(X_raw)

        # ── Predict ──────────────────────────────────────────
        if self.label_encoder is not None:
            pred_enc   = model.predict(X)[0]
            pred_label = self.label_encoder.inverse_transform([pred_enc])[0]
        else:
            pred_idx   = int(model.predict(X)[0])
            pred_label = (
                self.classes[pred_idx]
                if 0 <= pred_idx < len(self.classes)
                else "Unclassified"
            )

        # ── Probabilities ────────────────────────────────────
        probabilities = {}
        confidence    = 0.0
        if hasattr(model, "predict_proba"):
            proba = model.predict_proba(X)[0]
            confidence = float(np.max(proba)) * 100

            if self.label_encoder is not None:
                for idx, p in enumerate(proba):
                    try:
                        lbl = self.label_encoder.inverse_transform([idx])[0]
                    except Exception:
                        lbl = str(idx)
                    probabilities[lbl] = round(float(p) * 100, 2)
            else:
                for idx, p in enumerate(proba):
                    lbl = self.classes[idx] if idx < len(self.classes) else str(idx)
                    probabilities[lbl] = round(float(p) * 100, 2)

        # ── Feature Importance ───────────────────────────────────
        feature_importance = {}
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            total_importance = float(np.sum(importances))
            if total_importance > 0:
                pairs = sorted(
                    zip(self.features, importances),
                    key=lambda x: x[1],
                    reverse=True,
                )[:5]
                feature_importance = {
                    name: round((float(imp) / total_importance) * 100, 1)
                    for name, imp in pairs
                }

        return {
            "prediction":        pred_label,
            "confidence":        round(confidence, 2),
            "probabilities":     probabilities,
            "feature_importance": feature_importance,
            "description":       CLASS_DESCRIPTIONS.get(pred_label, "Diagnostic data under clinical review."),
            "recommendations":   (
                CLASS_RECOMMENDATIONS.get(pred_label, []) + GENERIC_RECOMMENDATIONS
            ),
            "model_used":        model_key,
            "fallback_used":     fallback_used,
            "status":            "success",
        }

    # ── Helpers ──────────────────────────────────────────────
    @staticmethod
    def _normalise_key(raw: str) -> str:
        key_map = {
            "random_forest": "random_forest", "randomforest": "random_forest", "rf": "random_forest",
            "svm": "svm", "support_vector_machine": "svm", "svc": "svm",
            "decision_tree": "decision_tree", "decisiontree": "decision_tree", "dt": "decision_tree",
            "logistic_regression": "logistic_regression",
            "logisticregression": "logistic_regression", "lr": "logistic_regression",
        }
        return key_map.get(raw.lower().strip(), "random_forest")


# ── Global singleton ─────────────────────────────────────────
model_manager = ModelManager()
