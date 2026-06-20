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
    role = db.Column(db.String(20), default='provider')  # admin, doctor, patient
    full_name = db.Column(db.String(120), nullable=True)
    hospital = db.Column(db.String(120), nullable=True)
    specialization = db.Column(db.String(120), nullable=True)
    proof_filename = db.Column(db.String(256), nullable=True)
    status = db.Column(db.String(20), default='pending')  # approved, pending, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    records = db.relationship(
        'DiagnosticRecord',
        backref='author',
        lazy='dynamic',
        foreign_keys='DiagnosticRecord.user_id',
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class Patient(db.Model):
    """Patient profile linked to a registered patient user account."""
    __tablename__ = 'patients'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, unique=True, index=True)
    patient_uuid = db.Column(db.String(36), unique=True, nullable=False, index=True)
    first_name = db.Column(db.String(64), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    date_of_birth = db.Column(db.Date, nullable=False)
    gender = db.Column(db.String(10))
    blood_group = db.Column(db.String(5))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('patient_profile', uselist=False))
    diagnostic_history = db.relationship(
        'DiagnosticRecord',
        backref='patient',
        lazy='dynamic',
        foreign_keys='DiagnosticRecord.patient_id',
    )


class DoctorPatientConnection(db.Model):
    """Relationship between a doctor (User) and a patient (Patient profile)."""
    __tablename__ = 'doctor_patient_connections'
    
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    doctor = db.relationship('User', backref=db.backref('patient_connections', lazy='dynamic'))
    patient = db.relationship('Patient', backref=db.backref('doctor_connections', lazy='dynamic'))


class DoctorTechnicianConnection(db.Model):
    """Relationship between a doctor (User) and a technician (User)."""
    __tablename__ = 'doctor_technician_connections'
    
    id = db.Column(db.Integer, primary_key=True)
    doctor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    technician_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, approved, rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    doctor = db.relationship('User', foreign_keys=[doctor_id], backref=db.backref('technician_connections', lazy='dynamic'))
    technician = db.relationship('User', foreign_keys=[technician_id], backref=db.backref('doctor_connections_tech', lazy='dynamic'))


class DiagnosticRecord(db.Model):
    """Records of specific AI-powered diagnostic sessions."""
    __tablename__ = 'diagnostic_records'
    
    id = db.Column(db.Integer, primary_key=True)
    patient_id = db.Column(db.Integer, db.ForeignKey('patients.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    patient_reference = db.Column(db.String(64), nullable=True)
    biomarkers_json = db.Column(db.Text, nullable=True)
    result_json = db.Column(db.Text, nullable=True)
    prediction_label = db.Column(db.String(64), nullable=False)
    confidence_score = db.Column(db.Float, nullable=False)
    model_version = db.Column(db.String(32))
    status = db.Column(db.String(20), default='draft')  # draft, approved
    doctor_remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    def to_dict(self):
        import json
        return {
            "id": self.id,
            "patient_reference": self.patient_reference,
            "prediction": self.prediction_label,
            "confidence": self.confidence_score,
            "model_used": self.model_version,
            "status": self.status,
            "doctor_remarks": self.doctor_remarks,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "biomarkers": json.loads(self.biomarkers_json) if self.biomarkers_json else {},
            "result": json.loads(self.result_json) if self.result_json else {},
        }


class ModelAuditLog(db.Model):
    """Audit logging for model performance and usage tracking."""
    __tablename__ = 'model_audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    model_key = db.Column(db.String(64), nullable=False)
    action = db.Column(db.String(64))  # load, predict, update
    status = db.Column(db.String(20))  # success, failure
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
