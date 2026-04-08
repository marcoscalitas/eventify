# Eventify — Event Reservation Platform

Eventify is a full-featured web application for discovering, creating, and reserving spots at events. Built with Django, Django REST Framework, and `django-role-permissions` on the back-end and vanilla JavaScript on the front-end, it provides a seamless, mobile-responsive experience for both event organizers and attendees.

## Distinctiveness and Complexity

Eventify is fundamentally distinct from every other project in the CS50W course. Unlike Project 4 (a social network focused on posts, follows, and likes), Eventify is an **event reservation management system** — there are no user profiles to follow, no feeds, no posts, and no social interactions. Unlike Project 2 (an e-commerce auction site with bidding mechanics), Eventify does not involve buying, selling, bidding, or any monetary transactions. Instead, it centers around a completely different domain: **event lifecycle management, role-based access control, and capacity-controlled reservations**.

### Role-Based Access Control (RBAC)

Eventify implements a full RBAC system using `django-role-permissions`. Two roles exist: **Attendee** and **Organizer**, each with distinct permissions. Attendees can browse, reserve, review, and favorite events. Organizers can additionally create, edit, and delete events, view attendee lists, and export them as CSV. The role is selected at registration and enforced both server-side (via a custom `@role_required` decorator that renders a proper 403 page) and in the UI (navbar and pages adapt based on the user's role). This goes far beyond the basic authentication in other course projects.

### Architecture: Django Best Practices

The codebase follows professional Django patterns: **fat models** with business logic encapsulated in model methods (`spots_left`, `average_rating`, `reserve`, `cancel`, `add_review`, `toggle_favorite`), **DRF serializers** for clean JSON API responses, and a **helpers module** for cross-cutting concerns like notification creation. Models, views, and serializers are organized into Python packages split by domain. Templates are grouped into subdirectories by feature area (auth, events, user, dashboard, notifications).

### Security & Reliability

- **Environment variables**: Secrets managed via `.env` with `python-dotenv` — `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` never hardcoded
- **Rate limiting**: All API endpoints protected with `django-ratelimit` (30/min for listings, 10/min for reservations, 5/min for reviews)
- **XSS prevention**: All user-generated content escaped via `escapeHtml()` in JavaScript template literals
- **CSRF protection**: All API endpoints use Django's CSRF cookie-based tokens
- **Production security**: HTTPS, HSTS, secure cookies, and `X-Content-Type-Options` headers automatically enabled when `DEBUG=False`

### Capacity Management & Data Integrity

The reservation system enforces capacity constraints with real-time availability checks. Database-level `unique_together` constraints prevent duplicate reservations, reviews, and favorites — even under concurrent requests. Organizers see occupancy statistics with progress bars in their dashboard.

### API Layer + Dynamic Frontend

The application features a full JSON API consumed by vanilla JavaScript: debounced search, category filtering, paginated results, AJAX-powered reservation/cancellation, toggle favorites, and star-rating review submissions — all without full page reloads. A custom `safeFetch()` wrapper provides consistent error handling with **toast notifications** for user feedback, and `setLoading()` prevents double-submit on buttons.

### Testing

The project includes a comprehensive test suite with **45 tests** across 7 test classes covering models, API endpoints, RBAC enforcement, form validation, page views, and authentication flows. Run with `python manage.py test reservations`.

### Additional Complexity

- **Review system**: 1-5 star ratings with accessible keyboard-navigable star buttons, only for users with confirmed reservations, one review per user per event, average rating computed via model method
- **Favorites**: Toggle via AJAX, dedicated favorites page
- **Organizer dashboard**: Event stats (occupancy %), attendee list, CSV export
- **User profiles**: Edit bio/avatar, public profile pages showing organized events
- **Notification system**: Real-time notification polling with mark-as-read, auto-created on reservation/cancellation
- **Toast notifications**: Non-intrusive feedback system replacing `alert()` calls, with success/error/info variants
- **Accessibility**: Skip-to-content link, ARIA labels on navigation and interactive elements, screen-reader-only text, keyboard-accessible star ratings
- **Custom error pages**: Styled 404, 403, and 500 pages extending the base layout
- **Admin improvements**: Readonly timestamps, autocomplete fields, inline reservations on events, bulk actions (activate/deactivate events, cancel reservations, mark notifications read)
- **Fully custom CSS**: CSS Grid, Flexbox, CSS custom properties, responsive breakpoints, toast animations — no external frameworks

## File Structure

### `eventify/` — Django Project Configuration
- **`settings.py`**: App registration, `django-role-permissions` config, `.env` integration via `python-dotenv`, security settings, rate limit config
- **`urls.py`**: Root URL configuration including `reservations.urls` and custom error handlers

### `reservations/models/` — Data Models (Package)
- **`__init__.py`**: Re-exports all models
- **`user.py`**: `UserProfile` — extends Django User with bio and avatar (OneToOneField)
- **`category.py`**: `Category` — event classification
- **`event.py`**: `Event` — full event data with `spots_left`, `average_rating`, `reserve()`, `add_review()`, `toggle_favorite()` methods
- **`reservation.py`**: `Reservation` — user-event link with confirmed/cancelled status and `cancel()` method
- **`review.py`**: `Review` — 1-5 star rating with comment, validated via Django validators
- **`favorite.py`**: `Favorite` — user-event bookmark

### `reservations/views/` — Views (Package)
- **`auth.py`**: Login, register (with role selection), logout
- **`user.py`**: Profile editing, public profile pages
- **`events.py`**: Homepage, event detail, create/edit event, my reservations, my favorites
- **`dashboard.py`**: Organizer dashboard with stats, attendee list, CSV export
- **`api.py`**: All REST API endpoints — events listing (paginated, searchable), reserve, cancel, review, toggle favorite

### `reservations/serializers/` — DRF Serializers (Package)
- **`events.py`**: `EventSerializer` — serializes Event with computed `spots_left` and `average_rating` fields

### `reservations/` — Core Files
- **`roles.py`**: RBAC role definitions (Attendee, Organizer) with permissions
- **`decorators.py`**: `@role_required` decorator — renders 403 page for browsers, JSON for AJAX
- **`helpers.py`**: `create_notification()` helper for cross-cutting notification logic
- **`forms.py`**: `RegisterForm`, `EventForm`, `ReviewForm` with validation
- **`urls.py`**: All page and API routes
- **`admin.py`**: Admin configuration with readonly fields, autocomplete, inlines, and bulk actions
- **`tests.py`**: 45 tests across 7 classes (models, API, RBAC, forms, pages, auth)

### `reservations/templates/` — Templates
- **`reservations/layout.html`**: Base template with role-aware navbar, skip-to-content link, notification polling
- **`reservations/auth/`**: `login.html`, `register.html`
- **`reservations/events/`**: `index.html` (homepage), `event_detail.html`, `event_form.html`, `my_favorites.html`
- **`reservations/user/`**: `profile.html`, `profile_public.html`, `my_reservations.html`
- **`reservations/dashboard/`**: `my_events.html`, `attendees.html`
- **`reservations/notifications/`**: `notifications.html`
- **`404.html`**, **`403.html`**, **`500.html`**: Custom error pages

### `reservations/static/reservations/`
- **`styles.css`**: Custom CSS (variables, grid, flexbox, responsive, toast animations, error pages, accessibility utilities)
- **`app.js`**: CSRF utility, mobile nav, `escapeHtml()`, `safeFetch()`, `setLoading()`, `showToast()`

### Root Files
- **`.env.example`**: Template for environment variables
- **`.gitignore`**: Ignores `.venv/`, `__pycache__/`, `db.sqlite3`, `.env`, etc.
- **`requirements.txt`**: Python dependencies

## How to Run

1. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your own SECRET_KEY and settings
   ```

4. **Apply migrations:**
   ```bash
   python manage.py makemigrations reservations
   python manage.py migrate
   ```

5. **Create a superuser:**
   ```bash
   python manage.py createsuperuser
   ```

6. **Run the tests:**
   ```bash
   python manage.py test reservations
   ```

7. **Run the server:**
   ```bash
   python manage.py runserver
   ```

8. **Setup**: Go to `/admin` to add categories (e.g., Music, Technology, Sports). Then register users via `/register` choosing either Attendee or Organizer role.

## Dependencies

| Package | Purpose |
|---|---|
| `django>=4.2` | Web framework |
| `djangorestframework>=3.15` | API serializers |
| `django-role-permissions>=3.2` | Role-based access control |
| `python-dotenv>=1.0` | Environment variable management |
| `django-ratelimit>=4.1` | API rate limiting |

## Additional Information

- **RBAC** is handled by `django-role-permissions`, configured in `reservations/roles.py`
- **Business logic** lives in model methods (fat models pattern), not in views
- **Notifications** are created automatically via `helpers.py` when reservations are made or cancelled
- Database-level `unique_together` constraints prevent duplicate reservations, reviews, and favorites
- No external CSS or JS frameworks are used — all styling and interactivity is custom
- The app runs on SQLite by default with no additional setup required
- In production, set `DEBUG=False` in `.env` to enable HTTPS/HSTS security headers automatically
# eventify
