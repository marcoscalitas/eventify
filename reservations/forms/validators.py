from django import forms


def validate_file_size(file, max_mb=5):
    max_size = max_mb * 1024 * 1024
    if file.size > max_size:
        raise forms.ValidationError(f"File size must be under {max_mb} MB.")
