from django import forms
from django.contrib.auth.models import User


class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)


class RegisterForm(forms.Form):
    ROLE_CHOICES = [
        ("attendee", "Attendee"),
        ("organizer", "Organizer"),
    ]

    username = forms.CharField(max_length=150, min_length=3)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, min_length=6)
    confirmation = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=ROLE_CHOICES, initial="attendee")

    def clean_username(self):
        username = self.cleaned_data["username"]
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Username already taken.")
        return username

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirmation = cleaned_data.get("confirmation")
        if password and confirmation and password != confirmation:
            raise forms.ValidationError("Passwords must match.")
        return cleaned_data
