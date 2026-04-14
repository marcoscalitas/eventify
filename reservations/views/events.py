from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from ..models import Category, Event, Favorite, Reservation, Review
from ..decorators import role_required
from ..forms import EventForm
from ..services.notification import notify_event_updated


def index(request):
    categories = Category.objects.all()
    return render(request, "reservations/events/index.html", {
        "categories": categories,
    })


def event_detail(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    reviews = event.reviews.select_related("user").order_by("-created_at")

    user_reservation = None
    user_favorited = False
    user_reviewed = False

    if request.user.is_authenticated:
        user_reservation = Reservation.objects.filter(
            user=request.user, event=event, status=Reservation.CONFIRMED
        ).first()

        user_favorited = Favorite.objects.filter(
            user=request.user, event=event
        ).exists()

        user_reviewed = Review.objects.filter(
            user=request.user, event=event
        ).exists()

    return render(request, "reservations/events/event_detail.html", {
        "event": event,
        "reviews": reviews,
        "user_reservation": user_reservation,
        "user_favorited": user_favorited,
        "user_reviewed": user_reviewed,
        "spots_left": event.spots_left(),
        "average_rating": event.average_rating(),
    })


def _render_event_form(request, form, event=None, editing=False):
    categories = Category.objects.all()
    context = {"form": form, "categories": categories, "editing": editing}
    if event:
        context["event"] = event
    return render(request, "reservations/events/event_form.html", context)


@role_required("organizer")
def create_event(request):
    if request.method != "POST":
        return _render_event_form(request, EventForm())

    form = EventForm(request.POST, request.FILES)
    if form.is_valid():
        event = form.save(commit=False)
        event.organizer = request.user
        event.save()
        return redirect("event_detail", event_id=event.id)

    return _render_event_form(request, form)


@role_required("organizer")
def edit_event(request, event_id):
    event = get_object_or_404(Event, pk=event_id, organizer=request.user)

    if request.method != "POST":
        return _render_event_form(request, EventForm(instance=event), event=event, editing=True)

    form = EventForm(request.POST, request.FILES, instance=event)
    if form.is_valid():
        form.save()
        notify_event_updated(event)
        return redirect("event_detail", event_id=event.id)

    return _render_event_form(request, form, event=event, editing=True)
