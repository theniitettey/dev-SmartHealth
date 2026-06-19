/**
 * Smart Health Sync v2.0 — Diagnosis Engine JavaScript
 * Author: Enock Queenson Eduafo | University of Ghana 2026
 */

"use strict";

// ── Feature order (matches backend FEATURE_ORDER) ─────────────
const FEATURES = [
    'Glucose', 'Cholesterol', 'Hemoglobin', 'Platelets',
    'White Blood Cells', 'Red Blood Cells', 'Hematocrit',
    'Mean Corpuscular Volume', 'Mean Corpuscular Hemoglobin',
    'Mean Corpuscular Hemoglobin Concentration',
    'Insulin', 'BMI', 'Systolic Blood Pressure', 'Diastolic Blood Pressure',
    'Triglycerides', 'HbA1c', 'LDL Cholesterol', 'HDL Cholesterol',
    'ALT', 'AST', 'Heart Rate', 'Creatinine', 'Troponin', 'C-reactive Protein'
];

// Clinical display names for print card
const FEATURE_LABELS = {
    'Glucose': 'Fasting Glucose (mg/dL)',
    'Cholesterol': 'Total Cholesterol (mg/dL)',
    'Hemoglobin': 'Haemoglobin (g/dL)',
    'Platelets': 'Platelets (×10³/µL)',
    'White Blood Cells': 'WBC (×10³/µL)',
    'Red Blood Cells': 'RBC (×10⁶/µL)',
    'Hematocrit': 'Haematocrit (%)',
    'Mean Corpuscular Volume': 'MCV (fL)',
    'Mean Corpuscular Hemoglobin': 'MCH (pg)',
    'Mean Corpuscular Hemoglobin Concentration': 'MCHC (g/dL)',
    'Insulin': 'Insulin (µIU/mL)',
    'BMI': 'BMI (kg/m²)',
    'Systolic Blood Pressure': 'Systolic BP (mmHg)',
    'Diastolic Blood Pressure': 'Diastolic BP (mmHg)',
    'Triglycerides': 'Triglycerides (mg/dL)',
    'HbA1c': 'HbA1c (%)',
    'LDL Cholesterol': 'LDL Cholesterol (mg/dL)',
    'HDL Cholesterol': 'HDL Cholesterol (mg/dL)',
    'ALT': 'ALT (U/L)',
    'AST': 'AST (U/L)',
    'Heart Rate': 'Heart Rate (bpm)',
    'Creatinine': 'Creatinine (mg/dL)',
    'Troponin': 'Troponin (ng/mL)',
    'C-reactive Protein': 'CRP (mg/L)',
};

const DISEASE_COLORS = {
    'Healthy':          '#C5E710',
    'Diabetes':         '#F4DF6B',
    'Anemia':           '#ff9966',
    'Heart Disease':    '#ff4757',
    'Thalassemia':      '#a855f7',
    'Thrombocytopenia': '#0099bb',
};

// ── Preset clinical profiles (normalised 0.0–1.0 values) ──────
const PRESETS = {
    healthy:  [0.12, 0.15, 0.65, 0.55, 0.45, 0.60, 0.58, 0.52, 0.55, 0.50,
               0.15, 0.22, 0.65, 0.45, 0.18, 0.10, 0.14, 0.65, 0.15, 0.14,
               0.18, 0.15, 0.05, 0.08],
    diabetes: [0.85, 0.45, 0.55, 0.62, 0.42, 0.52, 0.50, 0.48, 0.45, 0.42,
               0.72, 0.62, 0.45, 0.42, 0.55, 0.78, 0.48, 0.25, 0.45, 0.42,
               0.48, 0.52, 0.15, 0.55],
    anemia:   [0.42, 0.35, 0.15, 0.45, 0.42, 0.22, 0.18, 0.25, 0.22, 0.18,
               0.35, 0.45, 0.35, 0.32, 0.38, 0.38, 0.32, 0.45, 0.35, 0.32,
               0.65, 0.38, 0.12, 0.45],
    heart:    [0.52, 0.85, 0.45, 0.52, 0.55, 0.40, 0.40, 0.45, 0.42, 0.40,
               0.45, 0.58, 0.82, 0.78, 0.65, 0.48, 0.82, 0.15, 0.52, 0.48,
               0.85, 0.55, 0.88, 0.85],
};

// Stored last result for print card
let _lastResult = null;
let _lastFeatures = null;

// ── DOM Ready ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initModelSelector();
    initPresets();
    initForm();
});

// ── Model Selector ────────────────────────────────────────────
function initModelSelector() {
    const options = document.querySelectorAll('.model-option');
    const hidden  = document.getElementById('selectedModel');
    options.forEach(opt => {
        opt.addEventListener('click', () => {
            options.forEach(o => o.classList.remove('selected'));
            opt.classList.add('selected');
            if (hidden) hidden.value = opt.dataset.model;
        });
    });
}

// ── Presets ───────────────────────────────────────────────────
function initPresets() {
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => applyPreset(btn.dataset.preset));
    });
}

function applyPreset(key) {
    const values = PRESETS[key];
    if (!values) return;
    const inputs = document.querySelectorAll('.biomarker-input');
    inputs.forEach((input, i) => {
        if (values[i] !== undefined) {
            setTimeout(() => {
                input.value = values[i];
                clearFieldError(input);
                input.style.borderColor = 'var(--cyan-primary)';
                setTimeout(() => (input.style.borderColor = ''), 600);
            }, i * 25);
        }
    });
}

// ── Form ──────────────────────────────────────────────────────
function initForm() {
    const form = document.getElementById('predictionForm');
    if (!form) return;
    form.addEventListener('submit', async e => {
        e.preventDefault();
        await runDiagnosis();
    });

    // Live validation on blur
    document.querySelectorAll('.biomarker-input').forEach(input => {
        input.addEventListener('blur', () => validateSingleField(input));
        input.addEventListener('input', () => {
            if (input.classList.contains('invalid')) validateSingleField(input);
        });
    });
}

async function runDiagnosis() {
    const features = collectFeatures();
    if (!features) return;
    const model = document.getElementById('selectedModel')?.value || 'random_forest';

    const btn = document.getElementById('submitBtn');
    setLoading(btn, true);

    try {
        const res = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ features, model }),
        });

        const data = await res.json();

        if (!res.ok) {
            const msg = data.details
                ? `${data.error}\n\nDetails: ${JSON.stringify(data.details, null, 2)}`
                : (data.error || `HTTP ${res.status}`);
            showError(msg);
            return;
        }

        _lastResult   = data;
        _lastFeatures = features;
        setTimeout(() => showResult(data), 600);
    } catch (err) {
        showError('Network error: ' + err.message);
    } finally {
        setTimeout(() => setLoading(btn, false), 650);
    }
}

// ── Field Validation (A2) ─────────────────────────────────────
function validateSingleField(input) {
    const val = parseFloat(input.value);
    const feature = input.dataset.feature || '';
    const errId = 'err-' + input.id.replace('f-', '');
    const errEl = document.getElementById(errId);

    if (input.value === '' || isNaN(val)) {
        setFieldError(input, errEl, 'This field is required.');
        return false;
    }
    if (val < 0 || val > 1) {
        setFieldError(input, errEl, `Value must be between 0.0 and 1.0 (got ${val.toFixed(2)}).`);
        return false;
    }
    clearFieldError(input, errEl);
    return true;
}

function setFieldError(input, errEl, msg) {
    input.classList.add('invalid');
    if (errEl) { errEl.textContent = msg; errEl.classList.add('visible'); }
}
function clearFieldError(input, errEl) {
    input.classList.remove('invalid');
    if (errEl) errEl.classList.remove('visible');
}

function collectFeatures() {
    const inputs  = document.querySelectorAll('.biomarker-input');
    const dict    = {};
    let   valid   = true;

    inputs.forEach((input) => {
        if (!validateSingleField(input)) valid = false;
        const name = input.dataset.feature;
        const val  = parseFloat(input.value);
        if (!isNaN(val) && name) dict[name] = val;
    });

    if (!valid) {
        showError('Please correct the highlighted fields before running the diagnosis.');
        document.querySelector('.biomarker-input.invalid')?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        return null;
    }
    return dict;
}

// ── Results Panel ─────────────────────────────────────────────
function showResult(result) {
    const panel = document.getElementById('resultsPanel');
    if (!panel) return;

    panel.style.display = 'block';
    setTimeout(() => panel.classList.add('visible'), 10);

    const color = DISEASE_COLORS[result.prediction] || 'var(--cyan-primary)';

    // Diagnosis name
    const nameEl = document.getElementById('diagnosisName');
    if (nameEl) { nameEl.textContent = result.prediction || '—'; nameEl.style.color = color; }

    // Large confidence (A3/B1)
    const confLarge = document.getElementById('confidenceLarge');
    if (confLarge) confLarge.textContent = (result.confidence || 0).toFixed(1) + '%';

    // Model used label
    const modelLabel = document.getElementById('modelUsedLabel');
    if (modelLabel) {
        const mName = (result.model_used || '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
        modelLabel.textContent = 'Model: ' + mName + (result.fallback_used ? ' (fallback)' : '');
    }

    // Confidence bar
    const bar = document.getElementById('confidenceBar');
    if (bar) {
        const pct = result.confidence || 0;
        bar.style.width = '0%';
        setTimeout(() => {
            bar.style.width = pct + '%';
            bar.style.background = pct >= 80
                ? 'linear-gradient(90deg, #C5E710, #8E9630)'
                : pct >= 60
                    ? 'linear-gradient(90deg, #F4DF6B, #C5E710)'
                    : 'linear-gradient(90deg, #ff9966, #F4DF6B)';
        }, 50);
    }

    // Description
    const descEl = document.getElementById('diagnosisDescription');
    if (descEl) descEl.textContent = result.description || '';

    // Explanations (Why This Prediction Was Made)
    const expSection = document.getElementById('explanationSection');
    const expList = document.getElementById('clinicalExplanations');
    if (expSection && expList) {
        expList.innerHTML = '';
        const exps = result.explanations || [];
        if (exps.length > 0) {
            exps.forEach(exp => {
                const li = document.createElement('li');
                li.textContent = exp;
                expList.appendChild(li);
            });
            expSection.style.display = 'block';
        } else {
            expSection.style.display = 'none';
        }
    }

    // Feature Importance chart (A4/C1)
    renderFeatureImportance(result.feature_importance || {});

    // Probability bars
    const table = document.getElementById('probTable');
    if (table) {
        table.innerHTML = '';
        const sorted = Object.entries(result.probabilities || {}).sort(([, a], [, b]) => b - a);
        sorted.forEach(([name, prob]) => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td style="padding:8px 0;font-size:0.85rem;">${name}</td>
                <td class="prob-bar-cell">
                    <div class="prob-bar">
                        <div class="prob-fill" style="width:${prob}%;background:${DISEASE_COLORS[name] || 'var(--cyan-primary)'}"></div>
                    </div>
                </td>
                <td style="text-align:right;font-family:var(--font-mono);font-size:0.8rem;">${prob.toFixed(1)}%</td>`;
            table.appendChild(row);
        });
    }

    // Recommendations
    const list = document.getElementById('clinicalAdvice');
    if (list) {
        list.innerHTML = '';
        (result.recommendations || []).forEach(rec => {
            const li = document.createElement('li');
            li.textContent = rec;
            list.appendChild(li);
        });
    }

    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

// ── Feature Importance Chart (A4/C1) ─────────────────────────
function renderFeatureImportance(importanceMap) {
    const section   = document.getElementById('featureImportanceSection');
    const container = document.getElementById('fiChartContainer');
    if (!section || !container) return;

    const entries = Object.entries(importanceMap);
    if (entries.length === 0) { section.style.display = 'none'; return; }

    section.style.display = 'block';
    container.innerHTML   = '';

    const maxPct = Math.max(...entries.map(([, v]) => v));

    entries.forEach(([name, pct]) => {
        const displayName = FEATURE_LABELS[name] || name;
        const barWidth    = maxPct > 0 ? (pct / maxPct) * 100 : 0;

        const row = document.createElement('div');
        row.className = 'fi-row';
        row.innerHTML = `
            <div class="fi-label-row">
                <span>${displayName}</span>
                <span class="fi-pct">${pct.toFixed(1)}%</span>
            </div>
            <div class="fi-bar-outer">
                <div class="fi-bar-fill" data-width="${barWidth}"></div>
            </div>`;
        container.appendChild(row);

        // Animate bar after render
        requestAnimationFrame(() => {
            const fill = row.querySelector('.fi-bar-fill');
            if (fill) setTimeout(() => { fill.style.width = barWidth + '%'; }, 80);
        });
    });
}

// ── Print Result Card (C2) — results & advice only ───────────
function preparePrintCard() {
    if (!_lastResult) return;

    const ts  = new Date().toLocaleString();
    const ref = 'SHS-' + Date.now().toString(36).toUpperCase();

    document.getElementById('prc-ref').textContent = `Ref: ${ref}  ·  ${ts}`;

    const diagEl = document.getElementById('prc-diagnosis');
    if (diagEl) diagEl.textContent = _lastResult.prediction || '—';

    const confEl = document.getElementById('prc-conf');
    if (confEl) confEl.textContent = `Confidence Score: ${(_lastResult.confidence || 0).toFixed(1)}%`;

    const confFill = document.getElementById('prc-conf-fill');
    if (confFill) confFill.style.width = (_lastResult.confidence || 0) + '%';

    // Clinical description
    const descEl = document.getElementById('prc-desc');
    if (descEl) descEl.textContent = _lastResult.description || '';

    // Explanations for print card
    const prcTitle = document.getElementById('prc-explanation-title');
    const prcExps = document.getElementById('prc-explanations');
    if (prcTitle && prcExps) {
        prcExps.innerHTML = '';
        const exps = _lastResult.explanations || [];
        if (exps.length > 0) {
            exps.forEach(exp => {
                const li = document.createElement('li');
                li.textContent = exp;
                prcExps.appendChild(li);
            });
            prcTitle.style.display = 'block';
            prcExps.style.display = 'block';
        } else {
            prcTitle.style.display = 'none';
            prcExps.style.display = 'none';
        }
    }

    // Feature importance rows
    const fiRows = document.getElementById('prc-fi-rows');
    if (fiRows) {
        fiRows.innerHTML = '';
        const entries = Object.entries(_lastResult.feature_importance || {});
        if (entries.length === 0) {
            fiRows.innerHTML = '<p style="font-size:9pt;color:#777;">Feature importance not available for this model.</p>';
        } else {
            const maxV = Math.max(...entries.map(([, v]) => v));
            entries.forEach(([name, pct]) => {
                const w = maxV > 0 ? (pct / maxV) * 100 : 0;
                const row = document.createElement('div');
                row.className = 'prc-fi-row';
                row.innerHTML = `
                    <div class="prc-fi-label">${FEATURE_LABELS[name] || name}</div>
                    <div class="prc-fi-bar-outer"><div class="prc-fi-bar-fill" style="width:${w}%"></div></div>
                    <div class="prc-fi-pct">${pct.toFixed(1)}%</div>`;
                fiRows.appendChild(row);
            });
        }
    }

    // Clinical advice
    const adviceEl = document.getElementById('prc-advice');
    if (adviceEl) {
        adviceEl.innerHTML = '';
        (_lastResult.recommendations || []).forEach(rec => {
            const li = document.createElement('li');
            li.textContent = rec;
            adviceEl.appendChild(li);
        });
    }

    window.print();
}

// ── UI Helpers ────────────────────────────────────────────────
function setLoading(btn, loading) {
    if (!btn) return;
    btn.disabled = loading;
    btn.classList.toggle('loading', loading);
}

function showError(message) {
    const panel = document.getElementById('resultsPanel');
    if (panel) {
        panel.style.display = 'block';
        setTimeout(() => panel.classList.add('visible'), 10);
        const nameEl = document.getElementById('diagnosisName');
        const descEl = document.getElementById('diagnosisDescription');
        const confLarge = document.getElementById('confidenceLarge');
        if (nameEl) { nameEl.textContent = 'Diagnosis Error'; nameEl.style.color = 'var(--red-critical)'; }
        if (confLarge) confLarge.textContent = '—';
        if (descEl) descEl.textContent = message;
        const probTable = document.getElementById('probTable');
        if (probTable) probTable.innerHTML = '';
        const advice = document.getElementById('clinicalAdvice');
        if (advice) advice.innerHTML = '<li>Please check that all fields are filled correctly and try again.</li>';
        const fiSection = document.getElementById('featureImportanceSection');
        if (fiSection) fiSection.style.display = 'none';
        panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } else {
        alert('Error: ' + message);
    }
}
