from functools import wraps
from django.http import JsonResponse
from django.shortcuts import redirect, render
from rolepermissions.checkers import has_role


def role_required(role_name):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("login")
            if not has_role(request.user, role_name):
                is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
                return (
                    JsonResponse({"error": "Permission denied."}, status=403)
                    if is_ajax
                    else render(request, "403.html", status=403)
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator
