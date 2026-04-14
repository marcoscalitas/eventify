from django.db import models
from django.contrib.auth.models import User

from .base import SoftDeleteModel


class UserProfile(SoftDeleteModel):
    GENDER_CHOICES = [
        ("M", "Male"),
        ("F", "Female"),
        ("O", "Other"),
        ("N", "Prefer not to say"),
    ]

    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="profile")
    bio = models.TextField(blank=True, default="")
    avatar = models.ImageField(upload_to="avatars/", blank=True, default="")
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True, default="")
    phone = models.CharField(max_length=20, blank=True, default="")
    location = models.CharField(max_length=255, blank=True, default="")
    website = models.URLField(max_length=200, blank=True, default="")

    def __str__(self):
        return self.user.username
