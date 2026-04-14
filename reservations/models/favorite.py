from django.db import models
from django.contrib.auth.models import User

from .base import SoftDeleteModel
from .event import Event


class Favorite(SoftDeleteModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="favorites")
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="favorites")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_favorite",
            )
        ]

    def __str__(self):
        return f"{self.user.username} ♥ {self.event.title}"
