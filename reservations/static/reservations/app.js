// Utility: get CSRF cookie for Django
function getCookie(name) {
    if (!document.cookie) return null;
    for (const c of document.cookie.split(';')) {
        const cookie = c.trim();
        if (cookie.startsWith(name + '=')) {
            return decodeURIComponent(cookie.substring(name.length + 1));
        }
    }
    return null;
}

// Utility: escape HTML to prevent XSS
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Utility: safe fetch wrapper with error handling
function safeFetch(url, options = {}) {
    return fetch(url, options)
        .then(r => {
            if (!r.ok) {
                return r.json().catch(() => ({ error: `Request failed (${r.status})` }))
                    .then(data => { throw new Error(data.error || `Request failed (${r.status})`); });
            }
            return r.json();
        })
        .catch(err => {
            if (err.message === 'Failed to fetch') {
                showToast('Connection error. Check your network.', 'error');
            }
            throw err;
        });
}

// Utility: disable/enable button with loading state
function setLoading(btn, loading) {
    if (loading) {
        btn.disabled = true;
        btn.dataset.originalText = btn.textContent;
        btn.textContent = 'Loading...';
    } else {
        btn.disabled = false;
        btn.textContent = btn.dataset.originalText || btn.textContent;
    }
}

// Toast notification system
const TOAST_DURATION = 4000;
const RELOAD_DELAY = 800;

function showToast(message, type = 'success') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toast-container';
        container.setAttribute('aria-live', 'polite');
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.setAttribute('role', 'status');
    toast.textContent = message;
    container.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add('show'));

    setTimeout(() => {
        toast.classList.remove('show');
        toast.addEventListener('transitionend', () => toast.remove());
    }, TOAST_DURATION);
}

// Utility: POST action with loading state, toast, and optional reload
function postAction(btn, url) {
    setLoading(btn, true);
    return safeFetch(url, {
        method: 'POST',
        headers: { 'X-CSRFToken': getCookie('csrftoken') },
    })
    .catch(err => {
        showToast(err.message, 'error');
        setLoading(btn, false);
        throw err;
    });
}

// Utility: validate image file (type + size)
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
const MAX_IMAGE_SIZE = 5 * 1024 * 1024;

function validateImageFile(inputId) {
    const input = document.getElementById(inputId);
    if (!input.files || !input.files[0]) return true;
    const file = input.files[0];
    return ALLOWED_IMAGE_TYPES.includes(file.type) && file.size <= MAX_IMAGE_SIZE;
}

// Mobile nav toggle
document.addEventListener('DOMContentLoaded', () => {
    const toggle = document.getElementById('navToggle');
    const links = document.getElementById('navLinks');
    if (toggle && links) {
        toggle.addEventListener('click', () => {
            links.classList.toggle('active');
        });
    }
});
