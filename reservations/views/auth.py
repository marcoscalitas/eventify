from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from rolepermissions.roles import assign_role

from ..models import UserProfile
from ..forms import LoginForm, RegisterForm


def _is_ajax(request):
    return request.headers.get('Accept') == 'application/json'


def login_view(request):
    if request.method != "POST":
        return render(request, "reservations/auth/login.html")

    form = LoginForm(request.POST)
    ajax = _is_ajax(request)

    if not form.is_valid():
        msg = "Please fill in all fields correctly."
        if ajax:
            return JsonResponse({"error": msg}, status=400)
        return render(request, "reservations/auth/login.html", {"message": msg})

    user = authenticate(
        request,
        username=User.objects.filter(email=form.cleaned_data["email"]).values_list("username", flat=True).first() or "",
        password=form.cleaned_data["password"],
    )
    if not user:
        msg = "Invalid email and/or password."
        if ajax:
            return JsonResponse({"error": msg}, status=400)
        return render(request, "reservations/auth/login.html", {"message": msg})

    login(request, user)
    if ajax:
        return JsonResponse({"redirect": "/"})
    return redirect("index")


def logout_view(request):
    logout(request)
    return redirect("index")


def register(request):
    if request.method != "POST":
        return render(request, "reservations/auth/register.html")

    form = RegisterForm(request.POST)
    ajax = _is_ajax(request)

    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0]
        if ajax:
            return JsonResponse({"error": first_error}, status=400)
        return render(request, "reservations/auth/register.html", {
            "message": first_error,
        })

    try:
        user = User.objects.create_user(
            form.cleaned_data["username"],
            form.cleaned_data["email"],
            form.cleaned_data["password"],
        )
    except IntegrityError:
        msg = "Username already taken."
        if ajax:
            return JsonResponse({"error": msg}, status=400)
        return render(request, "reservations/auth/register.html", {
            "message": msg,
        })

    UserProfile.objects.create(user=user)
    assign_role(user, form.cleaned_data["role"])

    login(request, user)
    if ajax:
        return JsonResponse({"redirect": "/"})
    return redirect("index")
