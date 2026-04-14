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

    def __str__(self):
        return f"{self.title} ({self.date})"
