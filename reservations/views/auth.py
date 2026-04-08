from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.shortcuts import redirect, render
from rolepermissions.roles import assign_role

from ..models import UserProfile
from ..forms import LoginForm, RegisterForm


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
            )
            if user:
                login(request, user)
                return redirect("index")
            return render(request, "reservations/auth/login.html", {
                "message": "Invalid username and/or password.",
            })
        return render(request, "reservations/auth/login.html", {
            "message": "Please fill in all fields correctly.",
        })
    return render(request, "reservations/auth/login.html")


def logout_view(request):
    logout(request)
    return redirect("index")


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.create_user(
                    form.cleaned_data["username"],
                    form.cleaned_data["email"],
                    form.cleaned_data["password"],
                )
            except IntegrityError:
                return render(request, "reservations/auth/register.html", {
                    "message": "Username already taken.",
                })

            UserProfile.objects.create(user=user)
            assign_role(user, form.cleaned_data["role"])

            login(request, user)
            return redirect("index")

        first_error = next(iter(form.errors.values()))[0]
        return render(request, "reservations/auth/register.html", {
            "message": first_error,
        })

    return render(request, "reservations/auth/register.html")
