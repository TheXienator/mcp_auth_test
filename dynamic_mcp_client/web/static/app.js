/**
 * Dynamic MCP Client - JavaScript
 */

// Toast notification helper
function showToast(message, type = 'info') {
    const toastEl = document.getElementById('notificationToast');
    const toast = new bootstrap.Toast(toastEl);

    const toastBody = toastEl.querySelector('.toast-body');
    toastBody.textContent = message;

    // Set color based on type
    toastEl.classList.remove('toast-success', 'toast-danger', 'toast-warning', 'toast-info');
    if (type) {
        toastEl.classList.add(`toast-${type}`);
    }

    toast.show();
}

// Format datetime
function formatDateTime(dateString) {
    if (!dateString) return 'Never';

    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;

    const diffHours = Math.floor(diffMins / 60);
    if (diffHours < 24) return `${diffHours}h ago`;

    const diffDays = Math.floor(diffHours / 24);
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
}

// Auto-refresh timestamps
function refreshTimestamps() {
    document.querySelectorAll('[data-timestamp]').forEach(el => {
        const timestamp = el.dataset.timestamp;
        el.textContent = formatDateTime(timestamp);
    });
}

// Refresh every minute
setInterval(refreshTimestamps, 60000);

// Initial load
document.addEventListener('DOMContentLoaded', function() {
    refreshTimestamps();
});

// Handle errors globally
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    showToast('An unexpected error occurred', 'danger');
});
