// app/static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    // Initialize all tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Auto-hide alerts after 5 seconds
    setTimeout(function() {
        var alerts = document.querySelectorAll('.alert');
        alerts.forEach(function(alert) {
            var bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        });
    }, 5000);

    // Handle priority and status badges styling
    document.querySelectorAll('.priority-badge').forEach(function(badge) {
        var priority = badge.getAttribute('data-priority');
        if (priority === 'high' || priority === 'critical') {
            badge.classList.add('bg-danger');
        } else if (priority === 'medium') {
            badge.classList.add('bg-warning');
        } else {
            badge.classList.add('bg-success');
        }
    });

    document.querySelectorAll('.status-badge').forEach(function(badge) {
        var status = badge.getAttribute('data-status');
        if (status === 'open') {
            badge.classList.add('bg-secondary');
        } else if (status === 'in_progress') {
            badge.classList.add('bg-info');
        } else if (status === 'resolved') {
            badge.classList.add('bg-success');
        } else {
            badge.classList.add('bg-dark');
        }
    });
});