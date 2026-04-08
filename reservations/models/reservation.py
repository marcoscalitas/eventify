from django.db import models
from django.contrib.auth.models import User

from .event import Event


class Reservation(models.Model):
    STATUS_CHOICES = [
        ("confirmed", "Confirmed"),
        ("cancelled", "Cancelled"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reservations")
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="reservations")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="confirmed")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "event")

    def cancel(self):
        """Cancel this reservation and notify."""
        self.status = "cancelled"
        self.save()

        from ..helpers import notify_reservation_cancelled
        notify_reservation_cancelled(self.user, self.event)

    def __str__(self):
        return f"{self.user.username} → {self.event.title} ({self.status})"
