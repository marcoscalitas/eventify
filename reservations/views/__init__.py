from .auth import login_view, logout_view, register
from .user import profile, profile_public, my_reservations, my_favorites
from .events import index, event_detail, create_event, edit_event
from .dashboard import my_events, attendees, export_attendees_csv
from .notifications import notifications
from .api import (
    api_events, api_reserve, api_cancel, api_review,
    api_toggle_favorite, api_notifications, api_mark_read,
)
