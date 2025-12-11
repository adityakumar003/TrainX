// Auto-show modal if there are flash messages
document.addEventListener('DOMContentLoaded', function() {
    // Check if there are flash messages by looking for alert elements
    const alertElements = document.querySelectorAll('.modal-body .alert');
    
    if (alertElements.length > 0) {
        // Check if it's a successful login message
        const successAlert = document.querySelector('.modal-body .alert-success');
        if (successAlert && successAlert.textContent.includes('Login successful')) {
            // Don't show modal for successful login, just close it if open
            const modalElement = document.getElementById('loginSignupModal');
            const modal = bootstrap.Modal.getInstance(modalElement);
            if (modal) {
                modal.hide();
            }
            // Show a brief success notification
            showSuccessNotification('Login successful!');
        } else {
            // Show modal for other messages (errors, signup success, etc.)
            const modal = new bootstrap.Modal(document.getElementById('loginSignupModal'));
            modal.show();
        }
    }
});

// Function to show success notification
function showSuccessNotification(message) {
    // Create a temporary success alert at the top of the page
    const alertDiv = document.createElement('div');
    alertDiv.className = 'alert alert-success alert-dismissible fade show position-fixed';
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 10000; min-width: 300px;';
    alertDiv.innerHTML = `
        <strong>Success!</strong> ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // Auto-remove after 3 seconds
    setTimeout(function() {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 3000);
}
