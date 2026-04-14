from ..models import Favorite


def toggle_favorite(user, event):
    """Toggle favorite for a user. Returns True if favorited, False if removed."""
    existing = Favorite.all_objects.filter(user=user, event=event).first()

    if existing is None:
        Favorite.objects.create(user=user, event=event)
        return True

    if existing.deleted_at is None:
        existing.delete()
        return False

    existing.restore()
    return True
