/**
 * Smart Health Sync - Results Page JavaScript
 * Authors: Enock Queenson Eduafo & Christabel Araba Edumadze
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Colorize Confusion Matrices
    colorConfusionMatrices();

    // 2. Animate Matrix Cards and CV Cards on Scroll
    const resultObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                resultObserver.unobserve(entry.target);
            }
        });
    }, { threshold: 0.1 });

    document.querySelectorAll('.cv-card, .cm-card, .meth-card, .best-banner-card').forEach(card => {
        card.style.opacity = '0';
        card.style.transform = 'translateY(20px)';
        card.style.transition = 'all 0.6s cubic-bezier(0.17, 0.67, 0.83, 0.67)';
        resultObserver.observe(card);
    });

    // 2.b Animate Table Rows
    const tableRows = document.querySelectorAll('.metrics-table tbody tr');
    tableRows.forEach((row, index) => {
        row.style.opacity = '0';
        row.style.transform = 'translateY(10px)';
        row.style.transition = `all 0.4s ease ${index * 0.08}s`;
        setTimeout(() => {
            row.style.opacity = '1';
            row.style.transform = 'translateY(0)';
        }, 100);
    });

    // Handle reveals for result cards
    const obs = new IntersectionObserver(entries => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.style.opacity = '1';
                entry.target.style.transform = 'translateY(0)';
            }
        });
    });
    document.querySelectorAll('.cv-card, .cm-card, .meth-card, .best-banner-card').forEach(c => obs.observe(c));

    // 3. Highlight Matrix Diagonals Pulse
    setInterval(() => {
        document.querySelectorAll('.cm-diag').forEach(cell => {
            cell.classList.toggle('pulse-diag');
        });
    }, 2000);
});

function colorConfusionMatrices() {
    const cells = document.querySelectorAll('.cm-cell');
    
    // Find max value per table to scale colors
    const tables = document.querySelectorAll('.cm-table');
    tables.forEach(table => {
        let max = 0;
        const tableCells = table.querySelectorAll('.cm-cell');
        tableCells.forEach(c => {
            const val = parseInt(c.getAttribute('data-val'));
            if (val > max) max = val;
        });

        tableCells.forEach(cell => {
            const val = parseInt(cell.getAttribute('data-val'));
            const isDiag = cell.classList.contains('cm-diag');
            
            if (isDiag) {
                // Correct predictions (Diagonal) - Green shades
                const alpha = Math.max(0.1, val / max);
                cell.style.background = `rgba(197, 231, 16, ${alpha})`;
            } else if (val > 0) {
                // Errors - Red shades
                const alpha = Math.max(0.1, val / max);
                cell.style.background = `rgba(231, 76, 60, ${alpha})`;
            }
        });
    });
}

// Custom Result styles
const style = document.createElement('style');
style.textContent = `
    .pulse-diag {
        box-shadow: inset 0 0 10px rgba(197, 231, 16, 0.4);
        transition: all 1s ease-in-out;
    }
`;
document.head.appendChild(style);
