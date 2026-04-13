// ── Password policy ─────────────────────────────────────
const PASSWORD_REGEX = /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?]).{8,}$/;

function passwordRules() {
    return [
        { rule: 'required', errorMessage: 'Password is required.' },
        { rule: 'minLength', value: 8, errorMessage: 'At least 8 characters.' },
        {
            validator: (value) => PASSWORD_REGEX.test(value),
            errorMessage: 'Must include uppercase, lowercase, number and special character.',
        },
    ];
}

function confirmPasswordRules(passwordSelector) {
    return [
        { rule: 'required', errorMessage: 'Confirm your password.' },
        {
            validator: (value) => value === document.querySelector(passwordSelector).value,
            errorMessage: 'Passwords do not match.',
        },
    ];
}

// ── Image upload ────────────────────────────────────────
const ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif', 'image/webp'];
const MAX_IMAGE_SIZE = 5 * 1024 * 1024;

function validateImageFile(inputId) {
    const input = document.getElementById(inputId);
    if (!input.files || !input.files[0]) return true;
    const file = input.files[0];
    return ALLOWED_IMAGE_TYPES.includes(file.type) && file.size <= MAX_IMAGE_SIZE;
}

// ── Form error display ──────────────────────────────────
function showFormError(form, message) {
    const card = form.closest('.form-card');
    let alert = card.querySelector('.alert');
    if (!alert) {
        alert = document.createElement('div');
        alert.className = 'alert alert--error';
        card.insertBefore(alert, form);
    }
    alert.textContent = message;
}

// ── Async form submit ───────────────────────────────────
async function submitForm(form) {
    const btn = form.querySelector('[type="submit"]');
    setLoading(btn, true);

    try {
        const response = await fetch(form.action, {
            method: 'POST',
            headers: {
                'X-CSRFToken': getCookie('csrftoken'),
                'Accept': 'application/json',
            },
            body: new FormData(form),
        });

        const data = await response.json();

        if (!response.ok) {
            showFormError(form, data.error);
            setLoading(btn, false);
        } else {
            window.location.href = data.redirect;
        }
    } catch {
        showToast('Connection error. Please try again.', 'error');
        setLoading(btn, false);
    }
}
