from ..models import Reservation, Review
from .notification import notify_new_review


def add_review(user, event, rating, comment=""):
    """Add a review from a user. Returns (review, error)."""
    has_reservation = Reservation.objects.filter(
        user=user, event=event, status=Reservation.CONFIRMED
    ).exists()
    if not has_reservation:
        return None, "You must have a reservation to review."

    existing = Review.all_objects.filter(user=user, event=event).first()
    if existing is not None and existing.deleted_at is None:
        return None, "You already reviewed this event."

    if existing is not None:
        existing.restore()
        existing.rating = rating
        existing.comment = comment
        existing.save()
        notify_new_review(user, event, rating)
        return existing, None

    review = Review.objects.create(
        user=user, event=event, rating=rating, comment=comment
    )
    notify_new_review(user, event, rating)
    return review, None
