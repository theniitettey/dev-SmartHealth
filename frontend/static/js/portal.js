/**
 * Smart Health Sync — Portal Dashboard JavaScript
 */

"use strict";

document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.getElementById("sidebarToggle");
    const sidebar = document.getElementById("dashboardSidebar");
    if (toggle && sidebar) {
        toggle.addEventListener("click", () => sidebar.classList.toggle("open"));
    }
});

async function viewRecord(id, openPrint) {
    const modal = document.getElementById("recordModal");
    const body = document.getElementById("recordModalBody");
    if (!modal || !body) return;

    body.innerHTML = '<p style="color:var(--text-secondary);"><i class="fa-solid fa-spinner fa-spin"></i> Loading…</p>';
    modal.style.display = "flex";

    try {
        const res = await fetch("/api/history/" + id);
        const data = await res.json();
        if (!res.ok) {
            body.innerHTML = '<p class="text-danger">' + (data.error || "Failed to load record.") + '</p>';
            return;
        }
        const rec = data.record;
        const result = rec.result || {};
        const exps = result.explanations || [];
        const recs = result.recommendations || [];

        let html = `
            <div class="portal-section-title"><i class="fa-solid fa-file-medical"></i> Diagnosis Report</div>
            <div class="result-meta-row mb-3">
                <div>
                    <div class="confidence-value-large">${rec.prediction}</div>
                    <div class="confidence-label-small">Predicted Condition</div>
                </div>
                <div>
                    <div class="confidence-value-large">${(rec.confidence || 0).toFixed(1)}%</div>
                    <div class="confidence-label-small">Confidence Score</div>
                </div>
            </div>
            <p style="color:var(--text-secondary);font-size:0.9rem;">${result.description || ""}</p>
        `;

        if (exps.length) {
            html += `<div class="fi-title mt-3"><i class="fa-solid fa-circle-info"></i> Why This Prediction Was Made</div><ul class="explanation-list">`;
            exps.forEach(e => { html += `<li>${e}</li>`; });
            html += `</ul>`;
        }

        if (recs.length) {
            html += `<div class="fi-title mt-3"><i class="fa-solid fa-clipboard-list"></i> Clinical Recommendations</div><ul class="explanation-list">`;
            recs.forEach(r => { html += `<li>${r}</li>`; });
            html += `</ul>`;
        }

        html += `
            <div class="dash-status-item mt-3"><span>Date</span><span>${rec.created_at ? new Date(rec.created_at).toLocaleString() : "—"}</span></div>
            <div class="dash-status-item"><span>Model</span><span>${rec.model_used || "—"}</span></div>
            <div class="result-disclaimer mt-3">
                <div class="result-disclaimer-icon"><i class="fa-solid fa-triangle-exclamation"></i></div>
                <div><strong>Research Prototype</strong> — For clinical decision support only. All outputs must be verified by a licensed practitioner.</div>
            </div>
            <button class="print-result-btn mt-3" onclick="printRecordReport()"><i class="fa-solid fa-print"></i> Print Report</button>
        `;

        body.innerHTML = html;
        window._currentRecord = rec;

        if (openPrint) setTimeout(() => printRecordReport(), 400);
    } catch (err) {
        body.innerHTML = '<p class="text-danger">Network error loading record.</p>';
    }
}

function closeRecordModal() {
    const modal = document.getElementById("recordModal");
    if (modal) modal.style.display = "none";
}

function printRecordReport() {
    const rec = window._currentRecord;
    if (!rec) return;
    const result = rec.result || {};
    const exps = (result.explanations || []).map(e => `<li>${e}</li>`).join("");
    const recs = (result.recommendations || []).map(r => `<li>${r}</li>`).join("");

    const win = window.open("", "_blank");
    win.document.write(`
        <!DOCTYPE html><html><head><title>Diagnosis Report</title>
        <style>body{font-family:Georgia,serif;padding:36px;color:#111;}h1{font-size:22pt;}h2{font-size:11pt;text-transform:uppercase;color:#555;border-bottom:1px solid #ddd;padding-bottom:4px;}ul{line-height:1.7;} .conf{font-size:14pt;margin:12px 0;} .disc{background:#fff8e1;border:1px solid #f9a825;padding:10px;font-size:9pt;margin-top:20px;}</style>
        </head><body>
        <h1><i>Smart Health Sync</i> — Diagnosis Report</h1>
        <p>Ref: SHS-${rec.id} · ${rec.created_at ? new Date(rec.created_at).toLocaleString() : ""}</p>
        <h1 style="color:#2e7d32;">${rec.prediction}</h1>
        <p class="conf">Confidence Score: ${(rec.confidence || 0).toFixed(1)}%</p>
        <p>${result.description || ""}</p>
        ${exps ? `<h2>Why This Prediction Was Made</h2><ul>${exps}</ul>` : ""}
        ${recs ? `<h2>Clinical Recommendations</h2><ul>${recs}</ul>` : ""}
        <div class="disc"><strong>Disclaimer:</strong> Academic research prototype — not for unsupervised clinical use.</div>
        </body></html>
    `);
    win.document.close();
    win.print();
}
