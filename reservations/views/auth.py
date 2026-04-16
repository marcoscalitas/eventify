from django.contrib.auth import authenticate, get_user_model, login, logout
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import redirect, render
from rolepermissions.roles import assign_role

from ..forms import LoginForm, RegisterForm

User = get_user_model()


def _is_ajax(request):
    return request.headers.get('Accept') == 'application/json'


def _error_response(request, ajax, template, message):
    if ajax:
        return JsonResponse({"error": message}, status=400)
    return render(request, template, {"message": message})


def _success_response(ajax):
    if ajax:
        return JsonResponse({"redirect": "/"})
    return redirect("index")


_LOGIN_TEMPLATE = "reservations/auth/login.html"
_REGISTER_TEMPLATE = "reservations/auth/register.html"


def login_view(request):
    if request.method != "POST":
        return render(request, _LOGIN_TEMPLATE)

    form = LoginForm(request.POST)
    ajax = _is_ajax(request)

    if not form.is_valid():
        return _error_response(request, ajax, _LOGIN_TEMPLATE, "Please fill in all fields correctly.")

    user = authenticate(
        request,
        username=User.objects.filter(email=form.cleaned_data["email"]).values_list("username", flat=True).first() or "",
        password=form.cleaned_data["password"],
    )
    if not user:
        return _error_response(request, ajax, _LOGIN_TEMPLATE, "Invalid email and/or password.")

    login(request, user)
    return _success_response(ajax)


def logout_view(request):
    logout(request)
    return redirect("index")


def register(request):
    if request.method != "POST":
        return render(request, _REGISTER_TEMPLATE)

    form = RegisterForm(request.POST)
    ajax = _is_ajax(request)

    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0]
        return _error_response(request, ajax, _REGISTER_TEMPLATE, first_error)

    try:
        user = User.objects.create_user(
            form.cleaned_data["username"],
            form.cleaned_data["email"],
            form.cleaned_data["password"],
        )
    except IntegrityError:
        return _error_response(request, ajax, _REGISTER_TEMPLATE, "Username already taken.")

    assign_role(user, form.cleaned_data["role"])

    login(request, user)
    return _success_response(ajax)
