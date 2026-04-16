from django.conf import settings
from django.db import models
from django.utils import timezone

from .base import SoftDeleteManager, AllObjectsManager
from .event import Event


class Reservation(models.Model):
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (CONFIRMED, "Confirmed"),
        (CANCELLED, "Cancelled"),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="reservations")
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="reservations")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=CONFIRMED, db_index=True)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reservation_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="reservation_updated",
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_reservation",
            )
        ]

    def cancel(self):
        from ..services.notification import notify_reservation_cancelled
        self.status = self.CANCELLED
        self.save()
        notify_reservation_cancelled(self.user, self.event)

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    def __str__(self):
        return f"{self.user.username} → {self.event.title} ({self.status})"
