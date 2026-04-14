from rest_framework import serializers

from ..models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    type = serializers.CharField(source="notification_type")
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = ["id", "title", "message", "link", "is_read", "type", "created_at"]
