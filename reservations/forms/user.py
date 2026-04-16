from django import forms

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
    phone = forms.CharField(max_length=20, required=False)
