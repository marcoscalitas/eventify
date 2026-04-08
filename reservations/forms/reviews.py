from django import forms


class ReviewForm(forms.Form):
    rating = forms.IntegerField(min_value=1, max_value=5)
    comment = forms.CharField(required=False, max_length=1000)
