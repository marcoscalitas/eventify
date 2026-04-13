from django.db import models
from django.contrib.auth.models import User

from .base import SoftDeleteModel
from .event import Event


class Reservation(SoftDeleteModel):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (CONFIRMED, "Confirmed"),
        (CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reservations")
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="reservations")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=CONFIRMED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_reservation",
            )
        ]

    def cancel(self):
        self.status = self.CANCELLED
        self.save()

        from ..helpers import notify_reservation_cancelled
        notify_reservation_cancelled(self.user, self.event)

    def __str__(self):
        return f"{self.user.username} → {self.event.title} ({self.status})"
