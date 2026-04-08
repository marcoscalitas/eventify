from datetime import date

from django import forms

from ..models import Event
from .validators import validate_file_size


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title", "description", "category", "location",
            "date", "time", "capacity", "image",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "time": forms.TimeInput(attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].validators.append(validate_file_size)

    def clean_date(self):
        event_date = self.cleaned_data["date"]
        if event_date < date.today():
            raise forms.ValidationError("Event date must be in the future.")
        return event_date

    def clean_capacity(self):
        capacity = self.cleaned_data["capacity"]
        if capacity < 1:
            raise forms.ValidationError("Capacity must be at least 1.")
        return capacity
