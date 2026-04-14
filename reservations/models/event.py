from django.db import models
from django.contrib.auth.models import User
from django.utils.text import slugify

from .base import SoftDeleteModel
from .category import Category


class Event(SoftDeleteModel):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    STATUS_CHOICES = [
        (DRAFT, "Draft"),
        (PUBLISHED, "Published"),
        (CANCELLED, "Cancelled"),
        (COMPLETED, "Completed"),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    organizer = models.ForeignKey(User, on_delete=models.PROTECT, related_name="organized_events")
    venue = models.CharField(max_length=255)
    address = models.CharField(max_length=500, blank=True, default="")
    start_date = models.DateField()
    start_time = models.TimeField()
    end_date = models.DateField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    capacity = models.PositiveIntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    image = models.ImageField(upload_to="events/", blank=True, default="")
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PUBLISHED, db_index=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["start_date", "start_time"]

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.title)
            slug = base
            n = 1
            while Event.all_objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def is_free(self):
        return self.price == 0

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
        return f"{self.title} ({self.start_date})"
