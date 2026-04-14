from django.db import models
from django.contrib.auth.models import User

from .base import SoftDeleteModel


class Notification(SoftDeleteModel):
    TYPES = [
        ("reservation_confirmed", "Reservation Confirmed"),
        ("reservation_cancelled", "Reservation Cancelled"),
        ("new_review", "New Review"),
        ("event_updated", "Event Updated"),
        ("event_reminder", "Event Reminder"),
    ]

    recipient = models.ForeignKey(User, on_delete=models.PROTECT, related_name="notifications")
    notification_type = models.CharField(max_length=30, choices=TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    link = models.URLField(max_length=200, blank=True, default="")
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    @property
    def is_read(self):
        return self.read_at is not None

    def __str__(self):
        return f"{self.recipient.username}: {self.title}"
