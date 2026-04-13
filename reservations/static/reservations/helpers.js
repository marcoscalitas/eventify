// ── Cookie ───────────────────────────────────────────────
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

// ── XSS protection ──────────────────────────────────────
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ── Fetch wrapper ───────────────────────────────────────
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

// ── Loading state ───────────────────────────────────────
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

// ── Toast notifications ─────────────────────────────────
const TOAST_DURATION = 4000;
const RELOAD_DELAY = 800;

function showToast(message, type = 'success') {
    let container = document.getElementById('toastContainer');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toastContainer';
        container.className = 'toasts';
        container.setAttribute('aria-live', 'polite');
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast--${type}`;
    toast.setAttribute('role', 'status');
    toast.textContent = message;
    container.appendChild(toast);

    requestAnimationFrame(() => toast.classList.add('toast--show'));

    setTimeout(() => {
        toast.classList.remove('toast--show');
        toast.addEventListener('transitionend', () => toast.remove());
    }, TOAST_DURATION);
}

// ── POST action (button + toast + reload) ───────────────
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

// ── Confirm modal ───────────────────────────────────────
function showConfirm(message) {
    return new Promise((resolve) => {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal__overlay"></div>
            <div class="modal__content">
                <p class="modal__message">${escapeHtml(message)}</p>
                <div class="modal__actions">
                    <button class="modal__btn modal__btn--cancel" type="button">No</button>
                    <button class="modal__btn modal__btn--confirm" type="button">Yes</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        requestAnimationFrame(() => modal.classList.add('modal--active'));

        function close(result) {
            modal.classList.remove('modal--active');
            modal.addEventListener('transitionend', () => modal.remove());
            resolve(result);
        }

        modal.querySelector('.modal__btn--confirm').addEventListener('click', () => close(true));
        modal.querySelector('.modal__btn--cancel').addEventListener('click', () => close(false));
        modal.querySelector('.modal__overlay').addEventListener('click', () => close(false));
    });
}
