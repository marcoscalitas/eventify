from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Event, Favorite, Reservation
from ..forms import ProfileForm

User = get_user_model()


@login_required
def profile(request):
    if request.method != "POST":
        form = ProfileForm(initial={
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
            "bio": request.user.bio,
            "phone": request.user.phone,
        })
        return render(request, "reservations/user/profile.html", {
            "form": form,
        })

    form = ProfileForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "reservations/user/profile.html", {
            "form": form,
        })

    request.user.first_name = form.cleaned_data["first_name"]
    request.user.last_name = form.cleaned_data["last_name"]
    request.user.email = form.cleaned_data["email"]
    request.user.bio = form.cleaned_data["bio"]
    request.user.phone = form.cleaned_data["phone"]
    if form.cleaned_data["avatar"]:
        request.user.avatar = form.cleaned_data["avatar"]
    request.user.save()

    return redirect("profile")


def profile_public(request, username):
    user = get_object_or_404(User, username=username)
    events = user.organized_events.filter(status=Event.PUBLISHED).order_by("-start_date")

    return render(request, "reservations/user/profile_public.html", {
        "profile_user": user,
        "events": events,
    })


@login_required
def my_reservations(request):
    reservations = Reservation.objects.filter(
        user=request.user, status=Reservation.CONFIRMED
    ).select_related("event").order_by("event__start_date")
    return render(request, "reservations/user/my_reservations.html", {
        "reservations": reservations,
    })


@login_required
def my_favorites(request):
    favorites = Favorite.objects.filter(
        user=request.user
    ).select_related("event").order_by("-created_at")
    return render(request, "reservations/user/my_favorites.html", {
        "favorites": favorites,
    })
