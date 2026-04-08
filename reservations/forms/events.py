from django import forms

from ..models import Event


class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = [
            "title", "description", "category", "location",
            "date", "time", "capacity", "image_url",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "time": forms.TimeInput(attrs={"type": "time"}),
            "description": forms.Textarea(attrs={"rows": 5}),
        }

    def clean_capacity(self):
        capacity = self.cleaned_data["capacity"]
        if capacity < 1:
            raise forms.ValidationError("Capacity must be at least 1.")
        return capacity
