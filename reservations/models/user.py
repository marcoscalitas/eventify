from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

from .base import SoftDeleteManager, AllObjectsManager


class UserProfile(models.Model):
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
    deleted_at = models.DateTimeField(null=True, blank=True, default=None, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="userprofile_created",
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="userprofile_updated",
    )

    objects = SoftDeleteManager()
    all_objects = AllObjectsManager()

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save(update_fields=["deleted_at"])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=["deleted_at"])

    def __str__(self):
        return self.user.username
