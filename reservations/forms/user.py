from django import forms
from django.core.validators import MaxLengthValidator

from ..models import UserProfile
from .validators import validate_file_size


class ProfileForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    bio = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
    )
    avatar = forms.ImageField(required=False, validators=[validate_file_size])
    gender = forms.ChoiceField(
        choices=[("", "---")] + UserProfile.GENDER_CHOICES,
        required=False,
    )
    phone = forms.CharField(max_length=20, required=False)
    location = forms.CharField(max_length=255, required=False)
    website = forms.URLField(max_length=200, required=False)
