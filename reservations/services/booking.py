from django.db import IntegrityError

from ..models import Reservation
from .notification import notify_reservation_confirmed, notify_reservation_cancelled


def _reactivate(reservation):
    """Restore (if soft-deleted) and confirm a reservation."""
    if reservation.deleted_at is not None:
        reservation.restore()
    reservation.status = Reservation.CONFIRMED
    reservation.save()
    return reservation


def reserve(user, event):
    """Reserve a spot for a user. Returns (reservation, error)."""
    if event.spots_left() <= 0:
        return None, "No spots available."

    existing = Reservation.all_objects.filter(user=user, event=event).first()

    if existing is not None and existing.status == Reservation.CONFIRMED and existing.deleted_at is None:
        return None, "Already reserved."

    if existing is not None:
        reservation = _reactivate(existing)
        notify_reservation_confirmed(user, event)
        return reservation, None

    try:
        reservation = Reservation.objects.create(
            user=user, event=event, status=Reservation.CONFIRMED
        )
    except IntegrityError:
        return None, "Already reserved."

    notify_reservation_confirmed(user, event)
    return reservation, None


def cancel_reservation(reservation):
    """Cancel a reservation and notify."""
    reservation.status = Reservation.CANCELLED
    reservation.save()
    notify_reservation_cancelled(reservation.user, reservation.event)
