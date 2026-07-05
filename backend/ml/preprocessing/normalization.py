"""
Smart Health Sync — Biomarker Preprocessing Normalization
Approximated clinical reference ranges for min-max normalization.
Since the original training data's normalization parameters were not preserved,
these ranges are approximated based on standard clinical reference norms.
This is a documented limitation of the system.
"""

CLINICAL_RANGES = {
    "Glucose": (50.0, 300.0),                      # Normal fasting: 70-100 mg/dL
    "Cholesterol": (100.0, 400.0),                  # Desirable: <200 mg/dL
    "Hemoglobin": (5.0, 25.0),                     # Normal: 12-17.5 g/dL
    "Platelets": (50.0, 600.0),                    # Normal: 150-400 x10^3/µL
    "White Blood Cells": (1.0, 20.0),              # Normal: 4.5-11 x10^3/µL
    "Red Blood Cells": (2.0, 8.0),                 # Normal: 4.1-5.9 x10^6/µL
    "Hematocrit": (20.0, 60.0),                    # Normal: 35.5-48.6%
    "Mean Corpuscular Volume": (50.0, 120.0),      # Normal: 80-100 fL
    "Mean Corpuscular Hemoglobin": (15.0, 45.0),    # Normal: 27-33 pg
    "Mean Corpuscular Hemoglobin Concentration": (25.0, 40.0), # Normal: 32-36 g/dL
    "Insulin": (1.0, 100.0),                       # Fasting normal: 2-25 µIU/mL
    "BMI": (10.0, 50.0),                           # Healthy: 18.5-24.9 kg/m²
    "Systolic Blood Pressure": (70.0, 220.0),       # Normal: <120 mmHg
    "Diastolic Blood Pressure": (40.0, 130.0),      # Normal: <80 mmHg
    "Triglycerides": (30.0, 500.0),                # Normal: <150 mg/dL
    "HbA1c": (3.0, 15.0),                          # Normal: <5.7%
    "LDL Cholesterol": (30.0, 300.0),              # Optimal: <100 mg/dL
    "HDL Cholesterol": (10.0, 100.0),              # Normal: >40 mg/dL
    "ALT": (0.0, 200.0),                           # Normal: 7-56 U/L
    "AST": (0.0, 200.0),                           # Normal: 10-40 U/L
    "Heart Rate": (30.0, 200.0),                   # Normal resting: 60-100 bpm
    "Creatinine": (0.1, 10.0),                     # Normal: 0.5-1.2 mg/dL
    "Troponin": (0.0, 2.0),                        # Normal: <0.04 ng/mL
    "C-reactive Protein": (0.0, 100.0),            # Normal: <10 mg/L
}

def normalize_input(raw_values: dict) -> dict:
    """
    Min-max normalizes raw clinical values to 0-1 range based on standard clinical ranges.
    Clips values outside the min/max bounds so they don't produce values below 0 or above 1.
    Any non-biomarker values (like Widal titers) are passed through unchanged.
    """
    normalized = {}
    for k, v in raw_values.items():
        if k in CLINICAL_RANGES:
            try:
                val = float(v)
                min_val, max_val = CLINICAL_RANGES[k]
                if max_val == min_val:
                    norm_val = 0.0
                else:
                    norm_val = (val - min_val) / (max_val - min_val)
                # Clip to 0-1
                norm_val = max(0.0, min(1.0, norm_val))
                normalized[k] = norm_val
            except (ValueError, TypeError):
                normalized[k] = v
        else:
            normalized[k] = v
    return normalized
