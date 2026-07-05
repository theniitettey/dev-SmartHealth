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

    // Initialize notification polling if user is logged in
    const badge = document.getElementById("notifBadge");
    if (badge) {
        fetchNotifications();
        setInterval(fetchNotifications, 15000); // Poll every 15s
    }

    // Auto-load admin datasets table if present
    if (document.getElementById("datasetsListBody")) {
        loadDatasetsTable();
    }

    // Auto-load admin model metrics table if present
    if (document.getElementById("modelMetricsBody")) {
        loadModelMetrics();
    }

    // Render markdown content
    const aiReportText = document.querySelectorAll(".markdown-content");
    if (aiReportText.length > 0 && window.marked) {
        aiReportText.forEach(el => {
            el.innerHTML = marked.parse(el.textContent || el.innerText);
        });
    }

    // Auto-dismiss and acknowledge verification success notification (Component 3)
    const verificationAlert = document.getElementById("verificationSuccessAlert");
    if (verificationAlert) {
        const userId = window.USER_ID || "default";
        const ackKey = "verification_acknowledged_" + userId;
        if (localStorage.getItem(ackKey)) {
            verificationAlert.style.display = "none";
            verificationAlert.classList.add("d-none");
        } else {
            // Automatically dismiss after 4 seconds (4000ms)
            setTimeout(() => {
                verificationAlert.style.transition = "opacity 0.5s ease";
                verificationAlert.style.opacity = "0";
                setTimeout(() => {
                    verificationAlert.style.display = "none";
                    verificationAlert.classList.add("d-none");
                }, 500);
                localStorage.setItem(ackKey, "true");
            }, 4000);
        }
    }

    // Set dynamic max date to today for DOB inputs
    const todayStr = new Date().toISOString().split('T')[0];
    const newDobInput = document.getElementById("newPatientDOB");
    if (newDobInput) newDobInput.setAttribute("max", todayStr);
    const editDobInput = document.getElementById("editPatientDOB");
    if (editDobInput) editDobInput.setAttribute("max", todayStr);

    // Wire up notification pagination controls without inline onclick (Task 6)
    const btnNotifPrev = document.getElementById("btnNotifPrev");
    if (btnNotifPrev) {
        btnNotifPrev.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            changeNotifPage(-1);
        });
    }
    const btnNotifNext = document.getElementById("btnNotifNext");
    if (btnNotifNext) {
        btnNotifNext.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            changeNotifPage(1);
        });
    }

    // Prevent clicks inside notifications panel from propagating or triggering page scroll
    const notifPanel = document.getElementById("notificationsPanel");
    if (notifPanel) {
        notifPanel.addEventListener("click", (e) => {
            e.stopPropagation();
        });
    }
});

/* ── Notification Utilities ── */

let notifCurrentPage = 1;
const SHOWN_NOTIF_KEY = "shs_shown_notifications";

function getShownNotifIds() {
    try {
        const raw = localStorage.getItem(SHOWN_NOTIF_KEY);
        return raw ? new Set(JSON.parse(raw)) : new Set();
    } catch {
        return new Set();
    }
}

function saveShownNotifIds(set) {
    try {
        localStorage.setItem(SHOWN_NOTIF_KEY, JSON.stringify(Array.from(set)));
    } catch (err) {}
}

async function fetchNotifications(page = notifCurrentPage) {
    try {
        const res = await fetch(`/api/notifications?page=${page}&per_page=5`);
        const data = await res.json();
        if (!res.ok) return;

        notifCurrentPage = data.page || 1;

        const badge = document.getElementById("notifBadge");
        if (badge) {
            if (data.unread_count > 0) {
                badge.textContent = data.unread_count;
                badge.style.display = "inline-block";
            } else {
                badge.style.display = "none";
            }
        }

        const container = document.getElementById("notifListContainer");
        if (container) {
            if (data.notifications && data.notifications.length > 0) {
                let html = "";
                data.notifications.forEach(n => {
                    const dateObj = new Date(n.created_at);
                    const timeStr = dateObj.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
                    const dateStr = dateObj.toLocaleDateString([], { month: 'short', day: 'numeric' });
                    html += `
                        <div class="notif-item ${n.is_read ? 'read' : 'unread'}" onclick="markNotificationRead(${n.id})">
                            <div class="notif-msg">${n.message}</div>
                            <div class="notif-time">${dateStr} · ${timeStr}</div>
                        </div>
                    `;
                });
                container.innerHTML = html;
            } else {
                container.innerHTML = `<p class="text-muted p-3 text-center">No notifications</p>`;
            }
        }

        // Update pagination controls
        const prevBtn = document.getElementById("btnNotifPrev");
        const nextBtn = document.getElementById("btnNotifNext");
        const pageInfo = document.getElementById("notifPageInfo");
        
        if (pageInfo) {
            pageInfo.textContent = `Page ${data.page} of ${data.total_pages || 1}`;
        }
        if (prevBtn) {
            prevBtn.disabled = !data.has_prev;
            prevBtn.style.opacity = data.has_prev ? "1" : "0.5";
            prevBtn.style.cursor = data.has_prev ? "pointer" : "not-allowed";
        }
        if (nextBtn) {
            nextBtn.disabled = !data.has_next;
            nextBtn.style.opacity = data.has_next ? "1" : "0.5";
            nextBtn.style.cursor = data.has_next ? "pointer" : "not-allowed";
        }

        // Stacked Toast alerts (Component 3)
        showStackedToasts(data.notifications);

    } catch (err) {
        console.error("Error fetching notifications:", err);
    }
}

function changeNotifPage(direction) {
    fetchNotifications(notifCurrentPage + direction);
}

function showStackedToasts(notifications) {
    if (!notifications) return;
    
    let container = document.getElementById("toastNotificationsContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "toastNotificationsContainer";
        document.body.appendChild(container);
    }
    
    const shownIds = getShownNotifIds();
    let updated = false;
    
    notifications.forEach(n => {
        if (!n.is_read && !shownIds.has(n.id)) {
            shownIds.add(n.id);
            updated = true;
            
            const toast = document.createElement("div");
            toast.className = "floating-toast";
            toast.id = `toast-notif-${n.id}`;
            
            const timeStr = new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
            
            toast.innerHTML = `
                <div class="floating-toast-header">
                    <span><i class="fa-solid fa-circle-info"></i> New Notification</span>
                    <button class="floating-toast-close" onclick="dismissToastNotification(${n.id}, event)"><i class="fa-solid fa-xmark"></i></button>
                </div>
                <div class="floating-toast-body" onclick="clickToastNotification(${n.id})">${n.message}</div>
                <div style="font-size:0.65rem; color:var(--text-muted); text-align:right;">${timeStr}</div>
            `;
            
            container.appendChild(toast);
        }
    });
    
    if (updated) {
        saveShownNotifIds(shownIds);
    }
}

async function clickToastNotification(id) {
    await markNotificationRead(id);
    const toast = document.getElementById(`toast-notif-${id}`);
    if (toast) toast.remove();
}

async function dismissToastNotification(id, event) {
    if (event) {
        event.stopPropagation();
    }
    const toast = document.getElementById(`toast-notif-${id}`);
    if (toast) toast.remove();
    await markNotificationRead(id);
}

async function markNotificationRead(id) {
    try {
        await fetch(`/api/notifications/${id}/read`, { method: "POST" });
        fetchNotifications();
    } catch (err) {
        console.error("Error marking notification read:", err);
    }
}

async function readAllNotifications(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    try {
        const res = await fetch("/api/notifications/read-all", { method: "POST" });
        if (res.ok) {
            fetchNotifications();
        }
    } catch (err) {
        console.error("Error reading all notifications:", err);
    }
}

function toggleNotificationsPanel(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const panel = document.getElementById("notificationsPanel");
    if (panel) {
        if (panel.style.display === "none" || !panel.style.display) {
            panel.style.display = "block";
            document.body.classList.add("no-scroll");
            fetchNotifications();
        } else {
            panel.style.display = "none";
            document.body.classList.remove("no-scroll");
        }
    }
}

function closeNotificationsPanel(event) {
    if (event) {
        event.preventDefault();
        event.stopPropagation();
    }
    const panel = document.getElementById("notificationsPanel");
    if (panel) {
        panel.style.display = "none";
        document.body.classList.remove("no-scroll");
    }
}

document.addEventListener("click", (e) => {
    const panel = document.getElementById("notificationsPanel");
    const link = document.getElementById("notifSidebarLink");
    if (panel && panel.style.display === "block") {
        if (!panel.contains(e.target) && (!link || !link.contains(e.target))) {
            panel.style.display = "none";
            document.body.classList.remove("no-scroll");
        }
    }
});


/* ── Customizable PDF Builders & Printers ── */

function togglePrintSection(secName) {
    const checkbox = document.getElementById(`printSec_${secName}`);
    const sectionEl = document.getElementById(`reportSection_${secName}`);
    if (checkbox && sectionEl) {
        sectionEl.style.display = checkbox.checked ? "block" : "none";
    }
}

function loadHtml2PdfLibrary(callback) {
    if (window.html2pdf) {
        callback();
        return;
    }
    const script = document.createElement("script");
    script.src = "https://cdnjs.cloudflare.com/ajax/libs/html2pdf.js/0.10.1/html2pdf.bundle.min.js";
    script.onload = callback;
    document.head.appendChild(script);
}

function printCustomReport(id) {
    const reportEl = document.getElementById("printableReportCard");
    if (!reportEl) return;
    const printWindow = window.open("", "_blank");
    printWindow.document.write(`
        <html>
        <head>
            <title>Diagnosis Report - ${id}</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet">
            <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.6.0/css/all.min.css">
            <style>
                body {
                    background: #ffffff !important;
                    color: #111111 !important;
                    font-family: 'DM Sans', sans-serif;
                    padding: 40px;
                }
                .printable-report-wrapper {
                    border: none !important;
                    background: transparent !important;
                    padding: 0 !important;
                    color: #111111 !important;
                }
                h4, h5, strong, th, td {
                    color: #111111 !important;
                }
                .biomarkers-grid {
                    display: grid;
                    grid-template-columns: repeat(3, 1fr);
                    gap: 15px;
                    margin-top: 15px;
                }
                .biomarker-item {
                    border: 1px solid #ddd;
                    padding: 10px;
                    border-radius: 6px;
                }
                .biomarker-name {
                    font-size: 0.8rem;
                    color: #555;
                }
                .biomarker-val {
                    font-size: 1.1rem;
                    font-weight: 600;
                }
                .status-badge {
                    display: inline-block;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.8rem;
                    font-weight: bold;
                    text-transform: capitalize;
                }
                .status-approved {
                    background-color: #d4edda;
                    color: #155724;
                }
                .prob-bar {
                    height: 8px;
                    background: #eeeeee !important;
                    border-radius: 4px;
                    overflow: hidden;
                    margin-top: 4px;
                    width: 100%;
                }
                .prob-fill {
                    height: 100%;
                    border-radius: 4px;
                    background: #8E9630 !important;
                }
                .prob-fill-neural {
                    height: 100%;
                    border-radius: 4px;
                    background: #a855f7 !important;
                }
                * {
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }
                @media print {
                    body { padding: 0; }
                    .no-print { display: none; }
                }
            </style>
        </head>
        <body>
            <div class="printable-report-wrapper">
                ${reportEl.innerHTML}
            </div>
            <script>
                window.onload = function() {
                    window.print();
                    setTimeout(function() { window.close(); }, 500);
                };
            </script>
        </body>
        </html>
    `);
    printWindow.document.close();
}

function downloadCustomReportPDF(id, patientRef) {
    const reportEl = document.getElementById("printableReportCard");
    if (!reportEl) {
        alert("Error: Report data element was not found. Please refresh the page.");
        return;
    }
    if (reportEl.innerText.trim().length < 50) {
        alert("Error: Diagnosis report content is too short or empty. Unable to generate PDF. Please reload the page.");
        return;
    }
    
    const opt = {
        margin:       10,
        filename:     `SmartHealth-Report-${patientRef || id}.pdf`,
        image:        { type: 'jpeg', quality: 0.98 },
        html2canvas:  { scale: 2, useCORS: true, backgroundColor: '#ffffff' },
        jsPDF:        { unit: 'mm', format: 'a4', orientation: 'portrait' }
    };
    
    loadHtml2PdfLibrary(() => {
        const clone = reportEl.cloneNode(true);
        clone.style.background = "#ffffff";
        clone.style.color = "#111111";
        clone.style.padding = "20px";
        clone.style.border = "none";
        
        clone.querySelectorAll("*").forEach(el => {
            el.style.color = "#111111";
            if (el.classList.contains("biomarker-item")) {
                el.style.border = "1px solid #dddddd";
                el.style.background = "#fafafa";
            }
            if (el.classList.contains("status-badge")) {
                el.style.background = "#d4edda";
                el.style.color = "#155724";
            }
            if (el.classList.contains("prob-bar")) {
                el.style.background = "#eeeeee";
                el.style.border = "none";
            }
            if (el.classList.contains("prob-fill")) {
                el.style.background = "#8E9630";
            }
            if (el.classList.contains("prob-fill-neural")) {
                el.style.background = "#a855f7";
            }
        });

        window.html2pdf().set(opt).from(clone).save();
    });
}


/* ── Super Admin Control Actions ── */

async function verifyDoctor(doctorId, action) {
    const alertBox = document.getElementById("verifyAlert");
    if (alertBox) alertBox.className = "alert d-none";

    try {
        const res = await fetch(`/api/admin/doctors/${doctorId}/verify`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ action: action })
        });
        const data = await res.json();
        if (!res.ok) {
            if (alertBox) {
                alertBox.textContent = data.error || "Failed to update doctor verification.";
                alertBox.className = "alert alert-danger";
            }
            return;
        }

        if (alertBox) {
            alertBox.textContent = data.message;
            alertBox.className = "alert alert-success";
        }
        
        // Update badge and actions cell dynamically
        const badge = document.getElementById("status-badge-" + doctorId);
        const actions = document.getElementById("actions-" + doctorId);
        if (badge) {
            badge.textContent = data.doctor_status;
            badge.className = "status-badge status-" + data.doctor_status;
        }
        if (actions) {
            actions.innerHTML = '<span class="text-muted" style="font-size:0.8rem;">No action required</span>';
        }

        setTimeout(() => location.reload(), 1000);
    } catch (err) {
        if (alertBox) {
            alertBox.textContent = "Network error updating status.";
            alertBox.className = "alert alert-danger";
        }
    }
}

async function toggleDoctorStatus(doctorId) {
    const alertBox = document.getElementById("userAlert");
    if (alertBox) alertBox.className = "alert d-none";

    try {
        const res = await fetch(`/api/admin/doctors/${doctorId}/toggle-status`, {
            method: "POST"
        });
        const data = await res.json();
        if (!res.ok) {
            if (alertBox) {
                alertBox.textContent = data.error || "Failed to toggle status.";
                alertBox.className = "alert alert-danger";
            }
            return;
        }

        if (alertBox) {
            alertBox.textContent = data.message;
            alertBox.className = "alert alert-success";
        }

        const badge = document.getElementById("manage-status-" + doctorId);
        const btn = document.getElementById("btn-toggle-" + doctorId);
        if (badge) {
            badge.textContent = data.doctor_status;
            badge.className = "status-badge status-" + data.doctor_status;
        }
        if (btn) {
            if (data.doctor_status === "approved") {
                btn.textContent = "Deactivate";
                btn.className = "btn-action-verify btn-reject";
                btn.style.background = "rgba(255,153,102,0.1)";
                btn.style.color = "#ff9966";
                btn.style.borderColor = "rgba(255,153,102,0.2)";
            } else {
                btn.textContent = "Activate";
                btn.className = "btn-action-verify btn-approve";
                btn.style.background = "rgba(197,231,16,0.1)";
                btn.style.color = "var(--green-ok)";
                btn.style.borderColor = "rgba(197,231,16,0.2)";
            }
        }
    } catch (err) {
        if (alertBox) {
            alertBox.textContent = "Network error.";
            alertBox.className = "alert alert-danger";
        }
    }
}

async function deleteDoctorAccount(doctorId) {
    if (!confirm("Are you sure you want to permanently delete this doctor account? This action cannot be undone.")) return;
    const alertBox = document.getElementById("userAlert");
    if (alertBox) alertBox.className = "alert d-none";

    try {
        const res = await fetch(`/api/admin/doctors/${doctorId}`, {
            method: "DELETE"
        });
        const data = await res.json();
        if (!res.ok) {
            if (alertBox) {
                alertBox.textContent = data.error || "Failed to delete account.";
                alertBox.className = "alert alert-danger";
            }
            return;
        }

        if (alertBox) {
            alertBox.textContent = data.message;
            alertBox.className = "alert alert-success";
        }
        setTimeout(() => location.reload(), 1000);
    } catch (err) {
        if (alertBox) {
            alertBox.textContent = "Network error.";
            alertBox.className = "alert alert-danger";
        }
    }
}

function filterAdminDoctorTable() {
    const query = document.getElementById("adminDoctorSearch").value.toLowerCase().trim();
    const rows = document.querySelectorAll("#adminDoctorsTable tbody tr.admin-doc-row");
    
    rows.forEach(row => {
        const name = row.getAttribute("data-name") || "";
        const email = row.getAttribute("data-email") || "";
        const license = row.getAttribute("data-license") || "";
        
        if (name.includes(query) || email.includes(query) || license.includes(query)) {
            row.classList.remove("d-none");
        } else {
            row.classList.add("d-none");
        }
    });
}

async function loadDatasetsTable() {
    const listBody = document.getElementById("datasetsListBody");
    if (!listBody) return;

    try {
        const res = await fetch("/api/admin/datasets");
        const data = await res.json();
        if (!res.ok) {
            listBody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Failed to load datasets: ${data.error}</td></tr>`;
            return;
        }

        if (data.datasets && data.datasets.length > 0) {
            let html = "";
            data.datasets.forEach(d => {
                const sizeKB = (d.size / 1024).toFixed(1);
                html += `
                    <tr>
                        <td><strong>${d.name}</strong></td>
                        <td>${sizeKB} KB</td>
                        <td>${d.lines} rows</td>
                        <td>
                            <button onclick="deleteDataset('${d.name}')" class="btn-action-verify btn-reject"><i class="fa-solid fa-trash-can"></i> Delete</button>
                        </td>
                    </tr>
                `;
            });
            listBody.innerHTML = html;
        } else {
            listBody.innerHTML = `<tr><td colspan="4" class="text-center text-muted">No datasets available.</td></tr>`;
        }
    } catch (err) {
        listBody.innerHTML = `<tr><td colspan="4" class="text-center text-danger">Network error loading datasets.</td></tr>`;
    }
}

async function uploadDatasetInline(event) {
    event.preventDefault();
    const alertBox = document.getElementById("datasetAlert");
    if (alertBox) alertBox.className = "alert d-none";

    const fileInput = document.getElementById("datasetFileInput");
    if (!fileInput || !fileInput.files || fileInput.files.length === 0) {
        alert("Please choose a CSV file to upload.");
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append("file", file);

    const btn = event.target.querySelector("button[type='submit']");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Uploading...`;
    }

    try {
        const res = await fetch("/api/admin/datasets/upload", {
            method: "POST",
            body: formData
        });
        const data = await res.json();
        if (!res.ok) {
            if (alertBox) {
                alertBox.textContent = data.error || "Upload failed.";
                alertBox.className = "alert alert-danger";
            }
            return;
        }

        if (alertBox) {
            alertBox.textContent = data.message;
            alertBox.className = "alert alert-success";
        }
        fileInput.value = "";
        loadDatasetsTable();
    } catch (err) {
        if (alertBox) {
            alertBox.textContent = "Network error uploading file.";
            alertBox.className = "alert alert-danger";
        }
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-cloud-arrow-up"></i> Upload & Replace`;
        }
    }
}

async function deleteDataset(filename) {
    if (!confirm(`Are you sure you want to delete the dataset '${filename}'?`)) return;
    const alertBox = document.getElementById("datasetAlert");
    if (alertBox) alertBox.className = "alert d-none";

    try {
        const res = await fetch(`/api/admin/datasets/${filename}`, {
            method: "DELETE"
        });
        const data = await res.json();
        if (!res.ok) {
            if (alertBox) {
                alertBox.textContent = data.error || "Failed to delete dataset.";
                alertBox.className = "alert alert-danger";
            }
            return;
        }

        if (alertBox) {
            alertBox.textContent = data.message;
            alertBox.className = "alert alert-success";
        }
        loadDatasetsTable();
    } catch (err) {
        if (alertBox) {
            alertBox.textContent = "Network error.";
            alertBox.className = "alert alert-danger";
        }
    }
}

async function loadModelMetrics() {
    const listBody = document.getElementById("modelMetricsBody");
    if (!listBody) return;

    try {
        const res = await fetch("/api/admin/model-metrics");
        const data = await res.json();
        if (!res.ok) {
            listBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Failed to load metrics.</td></tr>`;
            return;
        }

        const models = data.models || {};
        const mgrHealth = data.model_manager_status || {};
        
        let html = "";
        for (const [mKey, mVal] of Object.entries(models)) {
            const nameFormatted = mKey.replace(/_/g, ' ').toUpperCase();
            const loaded = mgrHealth.loaded_models && mgrHealth.loaded_models.includes(mKey);
            const statusBadge = loaded 
                ? '<span class="status-badge status-approved">Loaded</span>' 
                : '<span class="status-badge status-rejected">Offline</span>';
                
            html += `
                <tr>
                    <td><strong>${nameFormatted}</strong></td>
                    <td>${(mVal.accuracy || 0).toFixed(3)}</td>
                    <td>${(mVal.precision || 0).toFixed(3)}</td>
                    <td>${(mVal.recall || 0).toFixed(3)}</td>
                    <td>${(mVal.f1_score || 0).toFixed(3)}</td>
                    <td>${(mVal.cv_mean || 0).toFixed(3)}</td>
                    <td>${statusBadge}</td>
                </tr>
            `;
        }
        listBody.innerHTML = html;
    } catch (err) {
        listBody.innerHTML = `<tr><td colspan="7" class="text-center text-danger">Network error.</td></tr>`;
    }
}

async function triggerModelRetraining() {
    const alertBox = document.getElementById("retrainAlert");
    if (alertBox) alertBox.className = "alert d-none";

    const btn = document.getElementById("btnRetrainModels");
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Retraining Pipeline Active...`;
    }

    try {
        const res = await fetch("/api/admin/model/retrain", {
            method: "POST"
        });
        const data = await res.json();
        if (!res.ok) {
            if (alertBox) {
                alertBox.textContent = data.error || "Retraining failed to launch.";
                alertBox.className = "alert alert-danger";
            }
            return;
        }

        if (alertBox) {
            alertBox.textContent = data.message;
            alertBox.className = "alert alert-success";
        }
        
        // Polling loop or log message simulation for 5s
        setTimeout(() => {
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = `<i class="fa-solid fa-arrows-spin"></i> Retrain All Models`;
            }
            loadModelMetrics();
        }, 5000);
    } catch (err) {
        if (alertBox) {
            alertBox.textContent = "Network error triggering retraining.";
            alertBox.className = "alert alert-danger";
        }
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `<i class="fa-solid fa-arrows-spin"></i> Retrain All Models`;
        }
    }
}


/* ── Patient Case Management JavaScript (Doctor View) ── */

function generatePatientUUID() {
    const chars = '0123456789ABCDEF';
    let suffix = '';
    for (let i = 0; i < 6; i++) {
        suffix += chars[Math.floor(Math.random() * 16)];
    }
    return 'PAT-' + suffix;
}

function prepareCreatePatientForm() {
    const form = document.getElementById("createPatientForm");
    if (form) form.reset();
    const uuidInput = document.getElementById("newPatientUUID");
    if (uuidInput) {
        uuidInput.value = generatePatientUUID();
    }
    const alertBox = document.getElementById("modalCreateAlert");
    if (alertBox) alertBox.classList.add("d-none");
}

function openCreatePatientModal() {
    prepareCreatePatientForm();
    const modalEl = document.getElementById('createPatientModal');
    if (modalEl) {
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    }
}

function openEditPatientModal(id, name, dob, gender, notes) {
    const idEl = document.getElementById("editPatientId");
    const nameEl = document.getElementById("editPatientName");
    const dobEl = document.getElementById("editPatientDOB");
    const genderEl = document.getElementById("editPatientGender");
    const notesEl = document.getElementById("editPatientNotes");

    if (idEl) idEl.value = id;
    if (nameEl) nameEl.value = name;
    if (dobEl) dobEl.value = dob;
    if (genderEl) genderEl.value = gender;
    if (notesEl) notesEl.value = notes || "";
    
    const alertBox = document.getElementById("modalEditAlert");
    if (alertBox) alertBox.classList.add("d-none");

    const modalEl = document.getElementById('editPatientModal');
    if (modalEl) {
        const modal = new bootstrap.Modal(modalEl);
        modal.show();
    }
}

function openViewPatientModal(id, name, dob, gender, notes, uuid) {
    const uuidEl = document.getElementById("viewPatientUUID");
    const nameEl = document.getElementById("viewPatientName");
    const dobEl = document.getElementById("viewPatientDOB");
    const genderEl = document.getElementById("viewPatientGender");
    const notesEl = document.getElementById("viewPatientNotes");

    if (uuidEl) uuidEl.value = uuid || "";
    if (nameEl) nameEl.value = name || "";
    if (dobEl) dobEl.value = dob || "";
    if (genderEl) genderEl.value = gender || "";
    if (notesEl) notesEl.value = notes || "No clinical notes recorded.";
    
    const modalEl = document.getElementById('viewPatientModal');
    if (modalEl) {
        let modal = bootstrap.Modal.getInstance(modalEl);
        if (!modal) {
            modal = new bootstrap.Modal(modalEl);
        }
        modal.show();
    }
}

function filterPatientTable() {
    const queryInput = document.getElementById("patientSearchInput");
    if (!queryInput) return;
    const query = queryInput.value.toLowerCase().trim();
    const rows = document.querySelectorAll("#patientsTable tbody tr.patient-row");
    
    rows.forEach(row => {
        const name = row.getAttribute("data-name").toLowerCase();
        const uuid = row.getAttribute("data-uuid").toLowerCase();
        const matches = name.includes(query) || uuid.includes(query);
        
        const btnArchived = document.getElementById("btnShowArchived");
        const isArchivedTab = btnArchived && btnArchived.classList.contains("active");
        const rowIsArchived = row.classList.contains("archived-row");
        
        if (matches) {
            if (isArchivedTab && rowIsArchived) {
                row.classList.remove("d-none");
            } else if (!isArchivedTab && !rowIsArchived) {
                row.classList.remove("d-none");
            } else {
                row.classList.add("d-none");
            }
        } else {
            row.classList.add("d-none");
        }
    });
}

function toggleArchivedView(showArchived) {
    const btnActive = document.getElementById("btnShowActive");
    const btnArchived = document.getElementById("btnShowArchived");
    
    if (showArchived) {
        if (btnActive) btnActive.classList.remove("active");
        if (btnArchived) btnArchived.classList.add("active");
    } else {
        if (btnActive) btnActive.classList.add("active");
        if (btnArchived) btnArchived.classList.remove("active");
    }
    
    const rows = document.querySelectorAll("#patientsTable tbody tr.patient-row");
    rows.forEach(row => {
        const rowIsArchived = row.classList.contains("archived-row");
        if (showArchived && rowIsArchived) {
            row.classList.remove("d-none");
        } else if (!showArchived && !rowIsArchived) {
            row.classList.remove("d-none");
        } else {
            row.classList.add("d-none");
        }
    });
    
    const searchInput = document.getElementById("patientSearchInput");
    if (searchInput && searchInput.value.trim()) {
        filterPatientTable();
    }
}

async function archivePatientCase(id, archive) {
    if (!confirm(`Are you sure you want to ${archive ? 'archive' : 'restore'} this patient case?`)) return;
    
    const alertBox = document.getElementById("patientManagerAlert");
    try {
        const res = await fetch(`/api/patients/${id}/archive`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ archive })
        });
        const data = await res.json();
        
        if (!res.ok) {
            if (alertBox) {
                alertBox.textContent = data.error || "Failed to update archive status.";
                alertBox.className = "alert alert-danger";
                alertBox.classList.remove("d-none");
            }
            return;
        }
        
        location.reload();
    } catch (err) {
        console.error("Archive error:", err);
    }
}

// Add Patient form submission handlers when DOM is ready
document.addEventListener("DOMContentLoaded", () => {
    const createForm = document.getElementById("createPatientForm");
    if (createForm) {
        createForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const alertBox = document.getElementById("modalCreateAlert");
            const btn = document.getElementById("savePatientBtn");
            
            const dobVal = document.getElementById("newPatientDOB").value;
            const todayStr = new Date().toISOString().split('T')[0];
            if (dobVal && dobVal > todayStr) {
                if (alertBox) {
                    alertBox.textContent = "Date of Birth cannot be in the future.";
                    alertBox.classList.remove("d-none");
                }
                if (btn) btn.disabled = false;
                return;
            }

            const payload = {
                patient_uuid: document.getElementById("newPatientUUID").value,
                full_name: document.getElementById("newPatientName").value.trim(),
                date_of_birth: dobVal,
                gender: document.getElementById("newPatientGender").value,
                clinical_notes: document.getElementById("newPatientNotes").value.trim()
            };
            
            if (btn) btn.disabled = true;
            try {
                const res = await fetch("/api/patients", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                
                if (!res.ok) {
                    if (alertBox) {
                        alertBox.textContent = data.error || "Failed to create patient case.";
                        alertBox.classList.remove("d-none");
                    }
                    if (btn) btn.disabled = false;
                    return;
                }
                
                const modalEl = document.getElementById('createPatientModal');
                if (modalEl) {
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
                }
                location.reload();
            } catch (err) {
                if (alertBox) {
                    alertBox.textContent = "Network error. Please try again.";
                    alertBox.classList.remove("d-none");
                }
                if (btn) btn.disabled = false;
            }
        });
    }

    const editForm = document.getElementById("editPatientForm");
    if (editForm) {
        editForm.addEventListener("submit", async (e) => {
            e.preventDefault();
            const alertBox = document.getElementById("modalEditAlert");
            const btn = document.getElementById("updatePatientBtn");
            const id = document.getElementById("editPatientId").value;
            
            const dobVal = document.getElementById("editPatientDOB").value;
            const todayStr = new Date().toISOString().split('T')[0];
            if (dobVal && dobVal > todayStr) {
                if (alertBox) {
                    alertBox.textContent = "Date of Birth cannot be in the future.";
                    alertBox.classList.remove("d-none");
                }
                if (btn) btn.disabled = false;
                return;
            }

            const payload = {
                full_name: document.getElementById("editPatientName").value.trim(),
                date_of_birth: dobVal,
                gender: document.getElementById("editPatientGender").value,
                clinical_notes: document.getElementById("editPatientNotes").value.trim()
            };
            
            if (btn) btn.disabled = true;
            try {
                const res = await fetch(`/api/patients/${id}`, {
                    method: "PUT",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify(payload)
                });
                const data = await res.json();
                
                if (!res.ok) {
                    if (alertBox) {
                        alertBox.textContent = data.error || "Failed to update patient case.";
                        alertBox.classList.remove("d-none");
                    }
                    if (btn) btn.disabled = false;
                    return;
                }
                
                const modalEl = document.getElementById('editPatientModal');
                if (modalEl) {
                    const modal = bootstrap.Modal.getInstance(modalEl);
                    if (modal) modal.hide();
                }
                location.reload();
            } catch (err) {
                if (alertBox) {
                    alertBox.textContent = "Network error. Please try again.";
                    alertBox.classList.remove("d-none");
                }
                if (btn) btn.disabled = false;
            }
        });
    }
});

function filterAdminActivityTable() {
    const select = document.getElementById("adminDoctorFilterSelect");
    const search = document.getElementById("adminDoctorSearchInput");
    if (!select || !search) return;
    
    const selectedDoctorId = select.value;
    const searchQuery = search.value.toLowerCase().trim();
    
    const rows = document.querySelectorAll(".admin-activity-row");
    rows.forEach(row => {
        const docId = row.getAttribute("data-doctor-id");
        const docName = row.getAttribute("data-doctor-name");
        
        let matchSelect = !selectedDoctorId || (docId === selectedDoctorId);
        let matchSearch = !searchQuery || (docName && docName.includes(searchQuery));
        
        if (matchSelect && matchSearch) {
            row.classList.remove("d-none");
            row.style.display = "";
        } else {
            row.classList.add("d-none");
            row.style.display = "none";
        }
    });
}
