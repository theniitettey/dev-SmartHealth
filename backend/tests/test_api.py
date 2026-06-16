"""
Smart Health Sync — Backend Test Suite
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026
"""

import json
import pytest
import sys
import os

# Allow importing from project root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.factory import create_app


@pytest.fixture
def app():
    """Create test Flask application instance."""
    os.environ["FLASK_ENV"] = "development"
    flask_app = create_app()
    flask_app.config["TESTING"] = True
    yield flask_app


@pytest.fixture
def client(app):
    """Return Flask test client."""
    return app.test_client()


# ── Health checks ─────────────────────────────────────────────
class TestHealthEndpoints:
    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_body(self, client):
        data = json.loads(client.get("/api/health").data)
        assert data["status"] == "online"
        assert "service" in data

    def test_health_models_returns_json(self, client):
        resp = client.get("/api/health/models")
        assert resp.content_type == "application/json"
        data = json.loads(resp.data)
        assert "loaded_models" in data
        assert "missing_models" in data
        assert "models_directory" in data


# ── Metadata ─────────────────────────────────────────────────
class TestMetadata:
    def test_metadata_endpoint(self, client):
        resp = client.get("/api/metadata")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["project"] == "Smart Health Sync"
        assert "endpoints" in data

    def test_models_list(self, client):
        resp = client.get("/api/models")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert "available_models" in data
        assert "features" in data
        assert len(data["features"]) == 24


# ── Prediction ───────────────────────────────────────────────
class TestPrediction:
    HEALTHY_FEATURES = {
        "Glucose": 0.12, "Cholesterol": 0.15, "Hemoglobin": 0.65,
        "Platelets": 0.55, "White Blood Cells": 0.45, "Red Blood Cells": 0.60,
        "Hematocrit": 0.58, "Mean Corpuscular Volume": 0.52,
        "Mean Corpuscular Hemoglobin": 0.55, "Mean Corpuscular Hemoglobin Concentration": 0.50,
        "Insulin": 0.15, "BMI": 0.22, "Systolic Blood Pressure": 0.65,
        "Diastolic Blood Pressure": 0.45, "Triglycerides": 0.18,
        "HbA1c": 0.10, "LDL Cholesterol": 0.14, "HDL Cholesterol": 0.65,
        "ALT": 0.15, "AST": 0.14, "Heart Rate": 0.18, "Creatinine": 0.15,
        "Troponin": 0.05, "C-reactive Protein": 0.08,
    }

    def test_predict_valid_input(self, client):
        payload = {"features": self.HEALTHY_FEATURES, "model": "random_forest"}
        resp = client.post("/api/predict",
                           data=json.dumps(payload),
                           content_type="application/json")
        # May be 200 or 503 depending on model availability in test environment
        assert resp.status_code in (200, 503)

    def test_predict_missing_features(self, client):
        payload = {"features": {"Glucose": 0.5}, "model": "random_forest"}
        resp = client.post("/api/predict",
                           data=json.dumps(payload),
                           content_type="application/json")
        assert resp.status_code in (400, 503)

    def test_predict_no_body(self, client):
        resp = client.post("/api/predict", content_type="application/json")
        assert resp.status_code == 400

    def test_predict_missing_features_key(self, client):
        payload = {"model": "random_forest"}
        resp = client.post("/api/predict",
                           data=json.dumps(payload),
                           content_type="application/json")
        assert resp.status_code == 400

    def test_predict_if_models_loaded(self, client):
        """If models are actually available, ensure full result structure."""
        hr = json.loads(client.get("/api/health/models").data)
        if not hr.get("loaded_models"):
            pytest.skip("No models loaded in test environment")

        payload = {"features": self.HEALTHY_FEATURES}
        resp = client.post("/api/predict",
                           data=json.dumps(payload),
                           content_type="application/json")
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data["status"] == "success"
        assert "prediction" in data
        assert "confidence" in data
        assert "probabilities" in data
        assert "recommendations" in data


# ── Pages ────────────────────────────────────────────────────
class TestPages:
    def test_index_page(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_predict_page(self, client):
        resp = client.get("/predict")
        assert resp.status_code == 200

    def test_results_page(self, client):
        resp = client.get("/results")
        assert resp.status_code == 200

    def test_about_page(self, client):
        resp = client.get("/about")
        assert resp.status_code == 200
