from django import forms
from django.core.validators import MaxLengthValidator


def validate_avatar_size(file):
    max_size = 5 * 1024 * 1024  # 5 MB
    if file.size > max_size:
        raise forms.ValidationError("Avatar file size must be under 5 MB.")


class ProfileForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    bio = forms.CharField(
        max_length=500,
        widget=forms.Textarea(attrs={"rows": 4}),
        required=False,
    )
    avatar = forms.ImageField(required=False, validators=[validate_avatar_size])
