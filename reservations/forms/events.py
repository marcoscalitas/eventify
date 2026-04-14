from datetime import date

from django import forms

from ..models import Event
from .validators import validate_file_size


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title", "description", "category", "venue", "address",
            "start_date", "start_time", "end_date", "end_time",
            "capacity", "price", "image",
        ]
        widgets = {
            "start_date": forms.DateInput(attrs={"type": "date"}),
            "start_time": forms.TimeInput(attrs={"type": "time"}),
            "end_date": forms.DateInput(attrs={"type": "date"}),
            "end_time": forms.TimeInput(attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 5}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["image"].validators.append(validate_file_size)

    def clean_start_date(self):
        event_date = self.cleaned_data["start_date"]
        if event_date < date.today():
            raise forms.ValidationError("Event date must be in the future.")
        return event_date

    def clean_capacity(self):
        capacity = self.cleaned_data["capacity"]
        if capacity < 1:
            raise forms.ValidationError("Capacity must be at least 1.")
        return capacity

    def clean(self):
        cleaned = super().clean()
        end_date = cleaned.get("end_date")
        start_date = cleaned.get("start_date")
        if end_date and start_date and end_date < start_date:
            raise forms.ValidationError("End date cannot be before start date.")
        return cleaned
