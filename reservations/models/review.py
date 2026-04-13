from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

from .base import SoftDeleteModel
from .event import Event


class Review(SoftDeleteModel):
    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reviews")
    event = models.ForeignKey(Event, on_delete=models.PROTECT, related_name="reviews")
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    comment = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "event"],
                condition=models.Q(deleted_at__isnull=True),
                name="unique_active_review",
            )
        ]

    def __str__(self):
        return f"{self.user.username} → {self.event.title} ({self.rating}★)"
