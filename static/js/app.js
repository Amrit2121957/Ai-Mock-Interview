// TalentMate - Modern JavaScript for Multi-page Application

document.addEventListener('DOMContentLoaded', function() {
    // Initialize common functionality
    initializeGlobalFeatures();
    
    // Initialize page-specific functionality based on current page
    const currentPage = window.location.pathname;
    
    switch(currentPage) {
        case '/':
        case '/home':
            initializeHomePage();
            break;
        case '/interview':
            initializeInterviewPage();
            break;
        case '/review':
            initializeReviewPage();
            break;
        case '/help':
            initializeHelpPage();
            break;
        case '/login':
        case '/register':
            initializeAuthPages();
            break;
    }
});

// Global features that work across all pages
function initializeGlobalFeatures() {
    // Flash message auto-hide
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            if (alert.classList.contains('alert-success')) {
                alert.style.transition = 'opacity 0.5s';
                alert.style.opacity = '0';
                setTimeout(() => alert.remove(), 500);
            }
        }, 5000);
    });

    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const href = this.getAttribute('href');
            
            // Validate href is more than just '#' and is a valid selector
            if (href && href.length > 1) {
                try {
                    const target = document.querySelector(href);
                    if (target) {
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                } catch (error) {
                    // Invalid selector, ignore
                    console.warn('Invalid selector for smooth scrolling:', href);
                }
            }
        });
    });

    // Add loading state to all forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function() {
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                const originalText = submitBtn.innerHTML;
                submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';
                
                // Re-enable after 10 seconds as fallback
                setTimeout(() => {
                    submitBtn.disabled = false;
                    submitBtn.innerHTML = originalText;
                }, 10000);
            }
        });
    });
}

// Home page specific functionality
function initializeHomePage() {
    // Add entrance animations
    const elements = document.querySelectorAll('.quote-container, .postcard, .feature-card');
    elements.forEach((element, index) => {
        element.style.opacity = '0';
        element.style.transform = 'translateY(30px)';
        element.style.transition = 'all 0.6s ease';
        
        setTimeout(() => {
            element.style.opacity = '1';
            element.style.transform = 'translateY(0)';
        }, index * 200);
    });

    // Enhanced postcard hover effects
    const postcard = document.querySelector('.postcard');
    if (postcard) {
        postcard.addEventListener('mouseenter', function() {
            this.style.transform = 'scale(1.05) rotate(2deg)';
        });
        
        postcard.addEventListener('mouseleave', function() {
            this.style.transform = 'scale(1) rotate(0deg)';
        });
    }
}

// Interview page functionality (already implemented in template)
function initializeInterviewPage() {
    // Additional interview page enhancements can go here
    console.log('Interview page initialized');
}

// Review page functionality (already implemented in template)
function initializeReviewPage() {
    // Additional review page enhancements can go here
    console.log('Review page initialized');
}

// Help page functionality
function initializeHelpPage() {
    // FAQ functionality is already in the template
    console.log('Help page initialized');
}

// Authentication pages functionality
function initializeAuthPages() {
    // Add form validation enhancements
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    passwordInputs.forEach(input => {
        input.addEventListener('focus', function() {
            this.parentElement.style.borderColor = '#667eea';
        });
        
        input.addEventListener('blur', function() {
            this.parentElement.style.borderColor = '#e9ecef';
        });
    });
}

// Utility functions
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} notification`;
    notification.style.cssText = `
        position: fixed;
        top: 100px;
        right: 20px;
        z-index: 9999;
        max-width: 400px;
        animation: slideInRight 0.3s ease;
    `;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" onclick="this.parentElement.remove()"></button>
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 5 seconds
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

function formatDate(dateString) {
    const options = { 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => {
            showNotification('Copied to clipboard!', 'success');
        });
    } else {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        showNotification('Copied to clipboard!', 'success');
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideInRight {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    .notification {
        animation: slideInRight 0.3s ease;
    }
    
    .loading-state {
        pointer-events: none;
        opacity: 0.7;
    }
    
    .fade-in {
        animation: fadeIn 0.5s ease;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; }
        to { opacity: 1; }
    }
`;
document.head.appendChild(style);

// Error handling for failed AJAX requests
window.addEventListener('unhandledrejection', function(event) {
    console.error('Unhandled promise rejection:', event.reason);
    showNotification('An error occurred. Please try again.', 'danger');
});

// Service worker registration for future offline support
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Service worker implementation can be added here in the future
        console.log('Service worker support detected');
    });
} 