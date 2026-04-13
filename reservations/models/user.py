from django.db import models
from django.contrib.auth.models import User

from .base import SoftDeleteModel


class UserProfile(SoftDeleteModel):
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="profile")
    bio = models.TextField(blank=True, default="")
    avatar = models.ImageField(upload_to="avatars/", blank=True, default="")

    def __str__(self):
        return self.user.username
