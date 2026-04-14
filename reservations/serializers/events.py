from rest_framework import serializers

from ..models import Event

DESCRIPTION_TRUNCATE_LENGTH = 150


class EventSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    organizer = serializers.SlugRelatedField(slug_field="username", read_only=True)
    spots_left = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    start_time = serializers.TimeField(format="%H:%M")
    end_time = serializers.TimeField(format="%H:%M", allow_null=True)
    is_free = serializers.BooleanField(read_only=True)

    class Meta:
        model = Event
        fields = [
            "id", "title", "slug", "description", "category", "venue", "address",
            "start_date", "start_time", "end_date", "end_time",
            "capacity", "spots_left", "price", "is_free", "image",
            "organizer", "average_rating", "status",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if self.context.get("truncate"):
            data["description"] = data["description"][:DESCRIPTION_TRUNCATE_LENGTH]

        if not instance.image:
            data["image"] = ""
        else:
            request = self.context.get("request")
            data["image"] = request.build_absolute_uri(instance.image.url) if request else instance.image.url
        return data
