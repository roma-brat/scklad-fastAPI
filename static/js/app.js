// Common JavaScript functions

// Highlight active sidebar link
function highlightActiveSidebarLink() {
    const currentPath = window.location.pathname;
    const links = document.querySelectorAll('.sidebar-link');
    
    links.forEach(function(link) {
        const href = link.getAttribute('href');
        if (href === currentPath) {
            link.classList.add('active');
        } else {
            link.classList.remove('active');
        }
    });
}

// Run on page load
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', highlightActiveSidebarLink);
} else {
    highlightActiveSidebarLink();
}

function showNotification(message, type = 'info') {
    const colors = {
        success: 'bg-green-500',
        error: 'bg-red-500',
        warning: 'bg-yellow-500',
        info: 'bg-blue-500'
    };
    
    const notification = document.createElement('div');
    notification.className = `${colors[type]} text-white px-6 py-3 rounded-lg shadow-lg fixed top-4 right-4 z-50`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.remove();
    }, 3000);
}

// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('ru-RU', {
        style: 'currency',
        currency: 'RUB',
        minimumFractionDigits: 0
    }).format(amount);
}

// Format date
function formatDate(date) {
    return new Intl.DateTimeFormat('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric'
    }).format(new Date(date));
}

// Debounce function
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Close modal
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.remove();
    }
}

// HTMX event handlers
document.body.addEventListener('htmx:responseError', function(evt) {
    showNotification('Ошибка при загрузке данных', 'error');
});

document.body.addEventListener('htmx:afterRequest', function(evt) {
    // Handle success notifications from server
    if (evt.detail.xhr.getResponseHeader('X-Notification')) {
        showNotification(
            evt.detail.xhr.getResponseHeader('X-Notification'),
            evt.detail.xhr.getResponseHeader('X-Notification-Type') || 'success'
        );
    }
});
