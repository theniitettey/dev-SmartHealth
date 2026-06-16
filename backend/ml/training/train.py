"""
Smart Health Sync — ML Training Pipeline
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026

Handles data loading, preprocessing, model selection, training, 
evaluation, and persistence of model artefacts.
"""

import os
import json
import logging
import shutil
import warnings
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, confusion_matrix, f1_score,
                             precision_score, recall_score)
from sklearn.model_selection import (StratifiedKFold, cross_val_score,
                                     train_test_split)
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier

# ── Config ───────────────────────────────────────────────────
warnings.filterwarnings('ignore')
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(message)s')
logger = logging.getLogger("smarthealth.train")

# ── Paths ────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
DATA_DIR = BASE_DIR / "datasets"
MODELS_ROOT = BASE_DIR / "models"
REGISTRY_DIR = BASE_DIR / "backend" / "ml" / "registry" / "models"

for d in [MODELS_ROOT, REGISTRY_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ── Feature Set ──────────────────────────────────────────────
FEATURES = [
    'Glucose', 'Cholesterol', 'Hemoglobin', 'Platelets',
    'White Blood Cells', 'Red Blood Cells', 'Hematocrit',
    'Mean Corpuscular Volume', 'Mean Corpuscular Hemoglobin',
    'Mean Corpuscular Hemoglobin Concentration', 'Insulin', 'BMI',
    'Systolic Blood Pressure', 'Diastolic Blood Pressure', 'Triglycerides',
    'HbA1c', 'LDL Cholesterol', 'HDL Cholesterol', 'ALT', 'AST',
    'Heart Rate', 'Creatinine', 'Troponin', 'C-reactive Protein'
]

DISEASE_LABELS = {
    'Healthy': 'Healthy', 'Diabetes': 'Diabetes', 'Anemia': 'Anemia',
    'Thalasse': 'Thalassemia', 'Thromboc': 'Thrombocytopenia', 'Heart Di': 'Heart Disease'
}

# ── Pipeline Class ───────────────────────────────────────────
class TrainingPipeline:
    def __init__(self):
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.models = {
            'logistic_regression': LogisticRegression(max_iter=2000, class_weight='balanced', random_state=42),
            'decision_tree': DecisionTreeClassifier(max_depth=12, class_weight='balanced', random_state=42),
            'random_forest': RandomForestClassifier(n_estimators=200, max_depth=15, class_weight='balanced', random_state=42),
            'svm': SVC(kernel='rbf', C=10, probability=True, class_weight='balanced', random_state=42)
        }
        self.results = []

    def load_data(self):
        logger.info("Loading datasets...")
        train_df = pd.read_csv(DATA_DIR / "train_data.csv")
        test_df = pd.read_csv(DATA_DIR / "test_data.csv")
        df = pd.concat([train_df, test_df], ignore_index=True)
        
        df['Disease'] = df['Disease'].map(DISEASE_LABELS).fillna(df['Disease'])
        df = df.dropna()
        
        X = df[FEATURES].values
        y = self.label_encoder.fit_transform(df['Disease'].values)
        
        return train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    def train_and_evaluate(self):
        X_train, X_test, y_train, y_test = self.load_data()
        
        logger.info("Scaling features...")
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        # Save preprocessing tools
        self._persist_artefact(self.scaler, "scaler.pkl")
        self._persist_artefact(self.label_encoder, "label_encoder.pkl")

        cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

        for name, model in self.models.items():
            logger.info(f"Training {name}...")
            model.fit(X_train_scaled, y_train)
            
            # Predict
            y_pred = model.predict(X_test_scaled)
            
            # Metrics
            acc = accuracy_score(y_test, y_pred)
            f1 = f1_score(y_test, y_pred, average='weighted')
            cv_scores = cross_val_score(model, X_train_scaled, y_train, cv=cv)
            
            logger.info(f"  {name} Result: Accuracy={acc:.4f}, F1={f1:.4f}, CV={cv_scores.mean():.4f}")
            
            # Save Model
            self._persist_artefact(model, f"{name}.pkl")
            
            self.results.append({
                'name': name.replace('_', ' ').title(),
                'key': name,
                'accuracy': round(float(acc), 4),
                'f1_score': round(float(f1), 4),
                'cv_mean': round(float(cv_scores.mean()), 4),
                'confusion_matrix': confusion_matrix(y_test, y_pred).tolist()
            })

    def _persist_artefact(self, obj, filename):
        for target_dir in [MODELS_ROOT, REGISTRY_DIR]:
            joblib.dump(obj, target_dir / filename)

    def save_summary(self):
        best_model = max(self.results, key=lambda x: x['f1_score'])
        logger.info(f"Best model: {best_model['name']}")
        
        summary = {
            'metadata': {
                'trained_at': datetime.utcnow().isoformat(),
                'author': 'Enock Queenson Eduafo & Christabel Araba Edumadze',
                'features': FEATURES
            },
            'best_model': best_model['name'],
            'best_model_key': best_model['key'],
            'models': self.results,
            'classes': list(self.label_encoder.classes_)
        }
        
        with open(MODELS_ROOT / "results_summary.json", 'w') as f:
            json.dump(summary, f, indent=2)
        shutil.copy(MODELS_ROOT / "results_summary.json", REGISTRY_DIR / "results_summary.json")

# ── Execute ──────────────────────────────────────────────────
if __name__ == "__main__":
    pipeline = TrainingPipeline()
    pipeline.train_and_evaluate()
    pipeline.save_summary()
    logger.info("Training pipeline completed successfully.")
