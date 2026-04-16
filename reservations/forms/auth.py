import re

from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

PASSWORD_REGEX = re.compile(
    r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()\-_+=\[\]{};:\'",.<>?/\\|]).{8,}$'
)
PASSWORD_ERROR = (
    "Password must be at least 8 characters with uppercase, "
    "lowercase, number and special character."
)


class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not PASSWORD_REGEX.match(password):
            raise forms.ValidationError(PASSWORD_ERROR)
        return password


class RegisterForm(forms.Form):
    ROLE_CHOICES = [
        ("attendee", "Attendee"),
        ("organizer", "Organizer"),
    ]

    username = forms.CharField(max_length=150, min_length=3)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)
    confirmation = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=ROLE_CHOICES, initial="attendee")

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already taken.")
        return username

    def clean_password(self):
        password = self.cleaned_data["password"]
        if not PASSWORD_REGEX.match(password):
            raise forms.ValidationError(PASSWORD_ERROR)
        return password

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("confirmation")
        if password and confirmation and password != confirmation:
            raise forms.ValidationError("Passwords must match.")
        return cleaned_data
