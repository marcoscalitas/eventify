from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    # Pages: Auth
    path("login", views.login_view, name="login"),
    path("logout", views.logout_view, name="logout"),
    path("register", views.register, name="register"),

    # Password Reset (Django built-in views)
    path("password-reset", auth_views.PasswordResetView.as_view(
        template_name="reservations/auth/password_reset.html",
        email_template_name="reservations/emails/password_reset_email.html",
        subject_template_name="reservations/emails/password_reset_subject.txt",
        success_url="/password-reset/done",
    ), name="password_reset"),
    path("password-reset/done", auth_views.PasswordResetDoneView.as_view(
        template_name="reservations/auth/password_reset_done.html",
    ), name="password_reset_done"),
    path("password-reset/<uidb64>/<token>", auth_views.PasswordResetConfirmView.as_view(
        template_name="reservations/auth/password_reset_confirm.html",
        success_url="/password-reset/complete",
    ), name="password_reset_confirm"),
    path("password-reset/complete", auth_views.PasswordResetCompleteView.as_view(
        template_name="reservations/auth/password_reset_complete.html",
    ), name="password_reset_complete"),

    # Pages: User profile
    path("profile", views.profile, name="profile"),
    path("profile/<str:username>", views.profile_public, name="profile_public"),

    # Pages: Events
    path("", views.index, name="index"),
    path("event/create", views.create_event, name="create_event"),
    path("event/<int:event_id>", views.event_detail, name="event_detail"),
    path("event/<int:event_id>/edit", views.edit_event, name="edit_event"),

    # Pages: User content
    path("my/reservations", views.my_reservations, name="my_reservations"),
    path("my/favorites", views.my_favorites, name="my_favorites"),

    # Pages: Notifications
    path("notifications", views.notifications, name="notifications"),

    # Pages: Organizer dashboard
    path("my/events", views.my_events, name="my_events"),
    path("my/events/<int:event_id>/attendees", views.attendees, name="attendees"),
    path("my/events/<int:event_id>/attendees/csv", views.export_attendees_csv, name="export_csv"),

    # API endpoints
    path("api/events", views.api_events, name="api_events"),
    path("api/event/<int:event_id>/reserve", views.api_reserve, name="api_reserve"),
    path("api/event/<int:event_id>/cancel", views.api_cancel, name="api_cancel"),
    path("api/event/<int:event_id>/review", views.api_review, name="api_review"),
    path("api/event/<int:event_id>/favorite", views.api_toggle_favorite, name="api_favorite"),
    path("api/notifications", views.api_notifications, name="api_notifications"),
    path("api/notifications/read", views.api_mark_read, name="api_mark_read"),
]
