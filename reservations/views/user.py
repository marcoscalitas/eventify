from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Favorite, Reservation, UserProfile
from ..forms import ProfileForm


@login_required
def profile(request):
    user_profile, _ = UserProfile.objects.get_or_create(user=request.user)

    if request.method != "POST":
        form = ProfileForm(initial={
            "first_name": request.user.first_name,
            "last_name": request.user.last_name,
            "email": request.user.email,
            "bio": user_profile.bio,
        })
        return render(request, "reservations/user/profile.html", {
            "user_profile": user_profile,
            "form": form,
        })

    form = ProfileForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "reservations/user/profile.html", {
            "user_profile": user_profile,
            "form": form,
        })

    user_profile.bio = form.cleaned_data["bio"]
    if form.cleaned_data["avatar"]:
        user_profile.avatar = form.cleaned_data["avatar"]
    user_profile.save()

    request.user.first_name = form.cleaned_data["first_name"]
    request.user.last_name = form.cleaned_data["last_name"]
    request.user.email = form.cleaned_data["email"]
    request.user.save()

    return redirect("profile")


def profile_public(request, username):
    user = get_object_or_404(User, username=username)
    user_profile, _ = UserProfile.objects.get_or_create(user=user)
    events = user.organized_events.filter(is_active=True).order_by("-date")

    return render(request, "reservations/user/profile_public.html", {
        "profile_user": user,
        "user_profile": user_profile,
        "events": events,
    })


@login_required
def my_reservations(request):
    reservations = Reservation.objects.filter(
        user=request.user, status=Reservation.CONFIRMED
    ).select_related("event").order_by("event__date")
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
