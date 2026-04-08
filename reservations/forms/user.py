from django import forms


class ProfileForm(forms.Form):
    first_name = forms.CharField(max_length=150, required=False)
    last_name = forms.CharField(max_length=150, required=False)
    email = forms.EmailField(required=False)
    bio = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), required=False)
    avatar = forms.ImageField(required=False)
