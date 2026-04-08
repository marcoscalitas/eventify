from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Category, Event, Favorite, Reservation, Review
from ..decorators import role_required
from ..forms import EventForm


def index(request):
    categories = Category.objects.all()
    return render(request, "reservations/events/index.html", {
        "categories": categories,
    })


def event_detail(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    reviews = event.reviews.select_related("user").order_by("-created_at")

    user_reserved = False
    user_reservation = None
    user_favorited = False
    user_reviewed = False

    if request.user.is_authenticated:
        try:
            user_reservation = Reservation.objects.get(
                user=request.user, event=event, status="confirmed"
            )
            user_reserved = True
        except Reservation.DoesNotExist:
            pass

        user_favorited = Favorite.objects.filter(
            user=request.user, event=event
        ).exists()

        user_reviewed = Review.objects.filter(
            user=request.user, event=event
        ).exists()

    return render(request, "reservations/events/event_detail.html", {
        "event": event,
        "reviews": reviews,
        "user_reserved": user_reserved,
        "user_reservation": user_reservation,
        "user_favorited": user_favorited,
        "user_reviewed": user_reviewed,
        "spots_left": event.spots_left(),
        "average_rating": event.average_rating(),
    })


@role_required("organizer")
def create_event(request):
    if request.method == "POST":
        form = EventForm(request.POST)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            return redirect("event_detail", event_id=event.id)
    else:
        form = EventForm()

    categories = Category.objects.all()
    return render(request, "reservations/events/event_form.html", {
        "form": form,
        "categories": categories,
        "editing": False,
    })


@role_required("organizer")
def edit_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id, organizer=request.user)

    if request.method == "POST":
        form = EventForm(request.POST, instance=event)
        if form.is_valid():
            form.save()
            event.notify_updated()
            return redirect("event_detail", event_id=event.id)
    else:
        form = EventForm(instance=event)

    categories = Category.objects.all()
    return render(request, "reservations/events/event_form.html", {
        "form": form,
        "event": event,
        "categories": categories,
        "editing": True,
    })


@login_required
def my_reservations(request):
    reservations = Reservation.objects.filter(
        user=request.user, status="confirmed"
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
