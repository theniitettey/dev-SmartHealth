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
    'Widal O Titer': 'Widal O Titer',
    'Widal H Titer': 'Widal H Titer',
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

const STORAGE_KEY = "shs_diagnosis_form_state";

function saveFormState() {
    const state = {
        patientId: document.getElementById('linkPatientSelect')?.value || "",
        patientRef: document.getElementById('patientReferenceInput')?.value || "",
        category: document.getElementById('diseaseCategorySelect')?.value || "all",
        biomarkers: {}
    };
    document.querySelectorAll('.biomarker-input').forEach(input => {
        state.biomarkers[input.id] = input.value;
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
}

function loadFormState() {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    try {
        const state = JSON.parse(raw);
        
        // Restore category first
        const categorySelect = document.getElementById('diseaseCategorySelect');
        if (categorySelect && state.category) {
            categorySelect.value = state.category;
            updateFieldVisibility(state.category);
        }
        
        const patientSelect = document.getElementById('linkPatientSelect');
        const refInput = document.getElementById('patientReferenceInput');
        if (patientSelect && state.patientId) {
            patientSelect.value = state.patientId;
            setTimeout(() => {
                const event = new Event('change');
                patientSelect.dispatchEvent(event);
                if (refInput && state.patientRef) {
                    refInput.value = state.patientRef;
                }
            }, 100);
        } else {
            if (refInput && state.patientRef) {
                refInput.value = state.patientRef;
            }
        }
        
        // Restore biomarkers
        if (state.biomarkers) {
            for (const [id, val] of Object.entries(state.biomarkers)) {
                const input = document.getElementById(id);
                if (input && val !== undefined) {
                    input.value = val;
                }
            }
        }
    } catch (e) {
        console.error("Error loading saved form state:", e);
    }
}

function clearFormState() {
    localStorage.removeItem(STORAGE_KEY);
    const form = document.getElementById('predictionForm');
    if (form) form.reset();
    
    const categorySelect = document.getElementById('diseaseCategorySelect');
    if (categorySelect) {
        categorySelect.value = "all";
        updateFieldVisibility("all");
    }
    
    const patientSelect = document.getElementById('linkPatientSelect');
    if (patientSelect) {
        patientSelect.value = "";
        const event = new Event('change');
        patientSelect.dispatchEvent(event);
    }
}

// ── DOM Ready ─────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    initPresets();
    initForm();
    initPatientLinking();
    initCategorySelector();
    
    // Bind state saving events
    document.getElementById('linkPatientSelect')?.addEventListener('change', saveFormState);
    document.getElementById('diseaseCategorySelect')?.addEventListener('change', saveFormState);
    document.querySelectorAll('.biomarker-input').forEach(input => {
        input.addEventListener('input', saveFormState);
    });
    
    // Clear form button
    document.getElementById('clearFormBtn')?.addEventListener('click', () => {
        if (confirm("Are you sure you want to clear all inputs?")) {
            clearFormState();
        }
    });

    // Initialize additional biomarkers search (Task 5)
    initAdditionalBiomarkersSearch();

    // Load saved form state
    loadFormState();
});

// ── Category Selection Visibility Control ─────────────────────
const CATEGORY_FIELDS = {
    all: [
        'Glucose', 'Cholesterol', 'Hemoglobin', 'Platelets', 'White Blood Cells', 'Red Blood Cells',
        'Hematocrit', 'Mean Corpuscular Volume', 'Mean Corpuscular Hemoglobin',
        'Mean Corpuscular Hemoglobin Concentration', 'Insulin', 'BMI', 'Systolic Blood Pressure',
        'Diastolic Blood Pressure', 'Triglycerides', 'HbA1c', 'LDL Cholesterol', 'HDL Cholesterol',
        'ALT', 'AST', 'Heart Rate', 'Creatinine', 'Troponin', 'C-reactive Protein'
    ],
    diabetes: ['Glucose', 'HbA1c', 'Cholesterol', 'BMI'],
    cardiovascular: ['Cholesterol', 'Troponin', 'Systolic Blood Pressure', 'Diastolic Blood Pressure', 'Platelets'],
    anemia: [
        'Hemoglobin', 'Red Blood Cells', 'Hematocrit', 'Mean Corpuscular Volume',
        'Mean Corpuscular Hemoglobin', 'Mean Corpuscular Hemoglobin Concentration'
    ],
    typhoid: ['Widal O Titer', 'Widal H Titer', 'White Blood Cells', 'AST', 'ALT']
};

function initCategorySelector() {
    const selector = document.getElementById('diseaseCategorySelect');
    if (!selector) return;
    selector.addEventListener('change', () => {
        updateFieldVisibility(selector.value);
    });
    // Set initial visibility
    updateFieldVisibility(selector.value);
}

function updateFieldVisibility(category) {
    manuallyAddedFeatures.clear();
    const visibleFeatures = CATEGORY_FIELDS[category] || CATEGORY_FIELDS.all;
    
    // Toggle input field column wrappers
    const inputs = document.querySelectorAll('.biomarker-input');
    inputs.forEach(input => {
        const featName = input.dataset.feature;
        const col = input.closest('.col-12');
        if (!col) return;
        
        if (visibleFeatures.includes(featName)) {
            col.style.display = 'block';
            col.classList.remove('d-none');
        } else {
            col.style.display = 'none';
            col.classList.add('d-none');
        }
    });

    // Toggle Typhoid only titles/wrappers
    const typhoidGroups = document.querySelectorAll('.typhoid-only-group');
    typhoidGroups.forEach(grp => {
        if (category === 'typhoid') {
            grp.style.display = 'block';
            grp.classList.remove('d-none');
        } else {
            grp.style.display = 'none';
            grp.classList.add('d-none');
        }
    });

    updateGroupHeaders();
    updateSearchableBiomarkers();
}

// ── Searchable Additional Biomarkers Dropdown Logic ──
const manuallyAddedFeatures = new Set();

function initAdditionalBiomarkersSearch() {
    const searchInput = document.getElementById("biomarkerSearchInput");
    const suggestionsList = document.getElementById("biomarkerSuggestionsList");
    if (!searchInput || !suggestionsList) return;

    searchInput.addEventListener("input", () => {
        const query = searchInput.value.toLowerCase().trim();
        const items = suggestionsList.querySelectorAll("li");
        let visibleCount = 0;
        
        items.forEach(item => {
            const text = item.textContent.toLowerCase();
            if (text.includes(query)) {
                item.style.display = "block";
                visibleCount++;
            } else {
                item.style.display = "none";
            }
        });

        suggestionsList.style.display = (query.length > 0 && visibleCount > 0) ? "block" : "none";
    });

    searchInput.addEventListener("focus", () => {
        updateSearchableBiomarkers();
        const query = searchInput.value.toLowerCase().trim();
        const items = suggestionsList.querySelectorAll("li");
        if (items.length > 0) {
            suggestionsList.style.display = "block";
        }
    });

    // Close suggestions when clicking outside
    document.addEventListener("click", (e) => {
        if (!searchInput.contains(e.target) && !suggestionsList.contains(e.target)) {
            suggestionsList.style.display = "none";
        }
    });
}

function updateSearchableBiomarkers() {
    const categorySelect = document.getElementById('diseaseCategorySelect');
    const category = categorySelect ? categorySelect.value : 'all';
    
    const additionalSection = document.getElementById('additionalBiomarkersSection');
    const suggestionsList = document.getElementById("biomarkerSuggestionsList");
    if (!suggestionsList) return;

    // Searchable dropdown is only needed if a specific category is selected (not "all" or "typhoid")
    if (category === 'all' || category === 'typhoid') {
        if (additionalSection) additionalSection.style.display = 'none';
        return;
    } else {
        if (additionalSection) additionalSection.style.display = 'block';
    }

    const visibleFeatures = CATEGORY_FIELDS[category] || CATEGORY_FIELDS.all;
    
    // Find all biomarkers from the 24 panel that are not visible and not manually added
    const remainingFeatures = FEATURES.filter(f => !visibleFeatures.includes(f) && !manuallyAddedFeatures.has(f));

    suggestionsList.innerHTML = "";
    remainingFeatures.forEach(f => {
        const li = document.createElement("li");
        li.textContent = f;
        li.style.padding = "8px 12px";
        li.style.cursor = "pointer";
        li.style.borderBottom = "1px solid var(--bg-border, #333)";
        
        li.addEventListener("mouseover", () => {
            li.style.background = "rgba(197, 231, 16, 0.08)";
            li.style.color = "var(--cyan-primary)";
        });
        li.addEventListener("mouseout", () => {
            li.style.background = "";
            li.style.color = "";
        });

        li.addEventListener("click", () => {
            manuallyAddedFeatures.add(f);
            
            // Unhide input field
            const inputs = document.querySelectorAll('.biomarker-input');
            inputs.forEach(input => {
                if (input.dataset.feature === f) {
                    const col = input.closest('.col-12');
                    if (col) {
                        col.style.display = 'block';
                        col.classList.remove('d-none');
                        // Highlight animation border
                        input.style.borderColor = 'var(--cyan-primary)';
                        setTimeout(() => (input.style.borderColor = ''), 1000);
                        input.focus();
                    }
                }
            });

            // Re-run group title check and suggestion lists
            updateGroupHeaders();
            updateSearchableBiomarkers();
            
            // Clear input
            const searchInput = document.getElementById("biomarkerSearchInput");
            if (searchInput) {
                searchInput.value = "";
            }
            suggestionsList.style.display = "none";
        });

        suggestionsList.appendChild(li);
    });
}

function updateGroupHeaders() {
    const groups = [
        { title: 'Metabolic Indices', selector: '#f-Glucose, #f-Insulin, #f-BMI, #f-HbA1c' },
        { title: 'Cardiovascular Metrics', selector: '#f-Cholesterol, #f-LDL, #f-HDL, #f-Triglycerides, #f-SBP, #f-DBP, #f-HR, #f-Troponin' },
        { title: 'Hematology', selector: '#f-Hemoglobin, #f-Platelets, #f-WBC, #f-RBC, #f-Hematocrit, #f-MCV, #f-MCH, #f-MCHC' },
        { title: 'Liver & Kidney Function', selector: '#f-ALT, #f-AST, #f-Creatinine, #f-CRP' }
    ];

    document.querySelectorAll('.biomarker-group-title').forEach(titleEl => {
        const titleText = titleEl.textContent.trim();
        const grp = groups.find(g => g.title === titleText);
        if (grp) {
            const elements = document.querySelectorAll(grp.selector);
            let anyVisible = false;
            elements.forEach(el => {
                const col = el.closest('.col-12');
                if (col && col.style.display !== 'none' && !col.classList.contains('d-none')) {
                    anyVisible = true;
                }
            });
            if (anyVisible) {
                titleEl.style.display = 'block';
                titleEl.classList.remove('d-none');
            } else {
                titleEl.style.display = 'none';
                titleEl.classList.add('d-none');
            }
        }
    });
}

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
        input.addEventListener('blur', () => {
            const col = input.closest('.col-12');
            const isHidden = col && (col.style.display === 'none' || col.classList.contains('d-none'));
            if (!isHidden) validateSingleField(input);
        });
        input.addEventListener('input', () => {
            if (input.classList.contains('invalid')) {
                const col = input.closest('.col-12');
                const isHidden = col && (col.style.display === 'none' || col.classList.contains('d-none'));
                if (!isHidden) validateSingleField(input);
            }
        });
    });
}

async function runDiagnosis() {
    const features = collectFeatures();
    if (!features) return;
    const model = document.getElementById('selectedModel')?.value || 'random_forest';
    const category = document.getElementById('diseaseCategorySelect')?.value || 'all';

    const patientSelect = document.getElementById('linkPatientSelect');
    const patientRefInput = document.getElementById('patientReferenceInput');

    const patient_id = patientSelect && patientSelect.value ? parseInt(patientSelect.value) : null;
    let patient_reference = patientRefInput ? patientRefInput.value.trim() : '';

    if (patientSelect && patientSelect.value && !patient_reference) {
        const selectedOption = patientSelect.options[patientSelect.selectedIndex];
        patient_reference = selectedOption.text.split(' (ID:')[0].trim();
    }

    const symptoms = {};
    if (category === 'typhoid') {
        symptoms.fever = document.getElementById('symp-fever')?.checked || false;
        symptoms.abdominal_pain = document.getElementById('symp-pain')?.checked || false;
        symptoms.headache = document.getElementById('symp-headache')?.checked || false;
        symptoms.diarrhea_constipation = document.getElementById('symp-diarrhea')?.checked || false;
        symptoms.fatigue = document.getElementById('symp-fatigue')?.checked || false;
    }

    const btn = document.getElementById('submitBtn');
    setLoading(btn, true);

    try {
        const payload = {
            features,
            category,
            model,
            patient_id,
            patient_reference,
            draft_id: window.selectedDraftId || null,
            symptoms
        };
        const res = await fetch('/api/predict', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
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
    // Relaxed validation to allow raw clinical values (non-negative numbers)
    if (val < 0) {
        setFieldError(input, errEl, `Value must be a positive number (got ${val.toFixed(2)}).`);
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
        const col = input.closest('.col-12');
        const isHidden = col && (col.style.display === 'none' || col.classList.contains('d-none'));
        if (isHidden) return;

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

    // Hook up review draft button
    const reviewBtn = document.getElementById("reviewDraftBtn");
    if (reviewBtn) {
        reviewBtn.onclick = () => {
            clearFormState();
            window.location.href = "/portal?section=view_record&record_id=" + result.record_id;
        };
    }
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

// ── Patient Selection & Search Filtering ───────────────────────
window.selectedDraftId = null;

function initPatientLinking() {
    const patientSelect = document.getElementById('linkPatientSelect');
    const patientRefInput = document.getElementById('patientReferenceInput');
    const refPreview = document.getElementById('referencePreview');
    const draftSelectRow = document.getElementById('draftSelectRow');
    const draftRecordSelect = document.getElementById('draftRecordSelect');

    function generateRandomSuffix() {
        const chars = '0123456789ABCDEF';
        let suffix = '';
        for (let i = 0; i < 6; i++) {
            suffix += chars[Math.floor(Math.random() * 16)];
        }
        return suffix;
    }

    function updatePreview() {
        if (refPreview && patientRefInput) {
            refPreview.textContent = "Preview: " + patientRefInput.value;
        }
    }

    const submitBtn = document.getElementById("submitBtn");
    function updateSubmitBtnState() {
        if (submitBtn && patientSelect) {
            submitBtn.disabled = (patientSelect.value === "");
        }
    }

    // Set initial reference
    if (patientRefInput && !patientRefInput.value) {
        patientRefInput.value = "PAT-GEN-" + generateRandomSuffix();
        updatePreview();
    }

    let patientDrafts = [];

    if (patientSelect && patientRefInput) {
        updateSubmitBtnState();
        patientSelect.addEventListener('change', async () => {
            updateSubmitBtnState();
            window.selectedDraftId = null;
            if (draftRecordSelect) {
                draftRecordSelect.innerHTML = '<option value="">-- Enter biomarkers manually --</option>';
            }
            if (draftSelectRow) draftSelectRow.style.display = 'none';

            if (patientSelect.value) {
                const selectedOption = patientSelect.options[patientSelect.selectedIndex];
                const patientUuid = selectedOption.getAttribute('data-uuid');
                patientRefInput.value = patientUuid || ("PAT-GEN-" + generateRandomSuffix());
                patientRefInput.readOnly = true;

                // Fetch patient drafts
                try {
                    const res = await fetch(`/api/doctor/patient/${patientSelect.value}/drafts`);
                    const data = await res.json();
                    if (data.status === 'success' && data.drafts && data.drafts.length > 0) {
                        patientDrafts = data.drafts;
                        patientDrafts.forEach(d => {
                            const opt = document.createElement('option');
                            opt.value = d.id;
                            opt.textContent = `Draft from ${d.created_at} (Ref: ${d.patient_reference})`;
                            draftRecordSelect.appendChild(opt);
                        });
                        if (draftSelectRow) draftSelectRow.style.display = 'flex';
                    }
                } catch (err) {
                    console.error("Error fetching patient drafts:", err);
                }
            } else {
                patientRefInput.value = "PAT-GEN-" + generateRandomSuffix();
                patientRefInput.readOnly = true;
            }
            updatePreview();
            saveFormState();
        });
    }

    if (draftRecordSelect) {
        draftRecordSelect.addEventListener('change', () => {
            const draftId = draftRecordSelect.value;
            if (draftId) {
                const draft = patientDrafts.find(d => d.id == draftId);
                if (draft) {
                    window.selectedDraftId = draft.id;
                    if (patientRefInput) {
                        patientRefInput.value = draft.patient_reference;
                        updatePreview();
                    }
                    // Auto populate biomarker inputs by data-feature
                    for (const [bmName, bmVal] of Object.entries(draft.biomarkers)) {
                        const input = document.querySelector(`.biomarker-input[data-feature="${bmName}"]`);
                        if (input) {
                            input.value = bmVal;
                            input.classList.remove('invalid');
                            const errId = 'err-' + input.id.replace('f-', '');
                            const errEl = document.getElementById(errId);
                            if (errEl) errEl.classList.remove('visible');
                        }
                    }
                    saveFormState();
                }
            } else {
                window.selectedDraftId = null;
            }
        });
    }

    // Auto-trigger if patient select is pre-populated
    if (patientSelect && patientSelect.value) {
        setTimeout(() => {
            const event = new Event('change');
            patientSelect.dispatchEvent(event);
        }, 100);
    }
}
