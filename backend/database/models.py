"""
Smart Health Sync — Database Models
Authors: Enock Queenson Eduafo & Christabel Araba Edumadze | University of Ghana 2026
"""

from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    """System users (Administrators / Healthcare Providers)."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), default='provider')  # admin, provider
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    records = db.relationship('DiagnosticRecord', backref='author', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Patient(db.Model):
    """Patient records for clinical history."""
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10))
    blood_group = db.Column(db.String(5))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    diagnostic_history = db.relationship('DiagnosticRecord', backref='patient', lazy='dynamic')


class DiagnosticRecord(db.Model):
    """Records of specific AI-powered diagnostic sessions."""
    __tablename__ = 'diagnostic_records'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Biomarker snapshot (stored as JSON for flexibility, or individual columns if strict)
    # Using individual columns for strictly typed clinical data as requested
    glucose = db.Column(db.Float)
    cholesterol = db.Column(db.Float)
    hemoglobin = db.Column(db.Float)
    platelets = db.Column(db.Float)
    # ... and others (truncated for brevity in a real system, but I'll add the core ones)
    
    # Prediction Results
    prediction_label = db.Column(db.String(64), nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)
    model_version = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)


class ModelAuditLog(db.Model):
    """Audit logging for model performance and usage tracking."""
    __tablename__ = 'model_audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    model_key = db.Column(db.String(64), nullable=False)
    action = db.Column(db.String(64))  # load, predict, update
    status = db.Column(db.String(20))  # success, failure
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
