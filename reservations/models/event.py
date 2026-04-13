from django.db import models
from django.contrib.auth.models import User

from .base import SoftDeleteModel
from .category import Category


class Event(SoftDeleteModel):
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    organizer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="organized_events")
    location = models.CharField(max_length=255)
    date = models.DateField()
    time = models.TimeField()
    capacity = models.PositiveIntegerField()
    image = models.ImageField(upload_to="events/", blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["date", "time"]

    def spots_left(self):
        from .reservation import Reservation
        confirmed = self.reservations.filter(status=Reservation.CONFIRMED).count()
        return self.capacity - confirmed

    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews.exists():
            return None
        return round(reviews.aggregate(models.Avg("rating"))["rating__avg"], 1)

    def reserve(self, user):
        """Reserve a spot for a user. Returns (reservation, error)."""
        from .reservation import Reservation
        from django.db import IntegrityError

        if self.spots_left() <= 0:
            return None, "No spots available."

        existing = Reservation.all_objects.filter(user=user, event=self).first()

        if existing is not None:
            if existing.deleted_at is not None:
                existing.restore()
                existing.status = Reservation.CONFIRMED
                existing.save()
            elif existing.status == Reservation.CONFIRMED:
                return None, "Already reserved."
            else:
                existing.status = Reservation.CONFIRMED
                existing.save()
            reservation = existing
        else:
            try:
                reservation = Reservation.objects.create(
                    user=user, event=self, status=Reservation.CONFIRMED
                )
            except IntegrityError:
                return None, "Already reserved."

        from ..helpers import notify_reservation_confirmed
        notify_reservation_confirmed(user, self)
        return reservation, None

    def add_review(self, user, rating, comment=""):
        """Add a review from a user. Returns (review, error)."""
        from .reservation import Reservation
        from .review import Review

        has_reservation = Reservation.objects.filter(
            user=user, event=self, status=Reservation.CONFIRMED
        ).exists()
        if not has_reservation:
            return None, "You must have a reservation to review."

        existing = Review.all_objects.filter(user=user, event=self).first()
        if existing is not None and existing.deleted_at is None:
            return None, "You already reviewed this event."

        if existing is not None:
            existing.restore()
            existing.rating = rating
            existing.comment = comment
            existing.save()
            review = existing
        else:
            review = Review.objects.create(
                user=user, event=self, rating=rating, comment=comment
            )

        from ..helpers import notify_new_review
        notify_new_review(user, self, rating)
        return review, None

    def toggle_favorite(self, user):
        """Toggle favorite for a user. Returns True if favorited, False if removed."""
        from .favorite import Favorite

        existing = Favorite.all_objects.filter(user=user, event=self).first()

        if existing is None:
            Favorite.objects.create(user=user, event=self)
            return True

        if existing.deleted_at is None:
            existing.delete()
            return False

        existing.restore()
        return True

    def notify_updated(self):
        """Notify all confirmed attendees that this event was updated."""
        from ..helpers import notify_event_updated
        notify_event_updated(self)

    def __str__(self):
        return f"{self.title} ({self.date})"
