from rest_framework import serializers

from ..models import Event


class EventSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    organizer = serializers.SlugRelatedField(slug_field="username", read_only=True)
    spots_left = serializers.IntegerField(read_only=True)
    average_rating = serializers.FloatField(read_only=True)
    time = serializers.TimeField(format="%H:%M")

    class Meta:
        model = Event
        fields = [
            "id", "title", "description", "category", "location",
            "date", "time", "capacity", "spots_left", "image_url",
            "organizer", "average_rating",
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Truncate description for list views
        if self.context.get("truncate"):
            data["description"] = data["description"][:150]
        return data
