import json

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.http import require_POST
from django_ratelimit.decorators import ratelimit

from ..models import Event, Notification, Reservation
from ..forms import ReviewForm
from ..serializers import EventSerializer, ReviewSerializer, NotificationSerializer


def ratelimited_error(request, exception):
    return JsonResponse({"error": "Too many requests. Please slow down."}, status=429)


@ratelimit(key="ip", rate="30/m", block=True)
def api_events(request):
    category = request.GET.get("category", "")
    search = request.GET.get("search", "")
    page = int(request.GET.get("page", 1))
    per_page = 12

    events = Event.objects.filter(is_active=True).select_related("category", "organizer")

    if category:
        events = events.filter(category__name=category)
    if search:
        events = events.filter(title__icontains=search)

    total = events.count()
    start = (page - 1) * per_page
    end = start + per_page
    page_events = events[start:end]

    serializer = EventSerializer(page_events, many=True, context={"truncate": True})
    return JsonResponse({
        "events": serializer.data,
        "page": page,
        "total_pages": (total + per_page - 1) // per_page,
        "total": total,
    })


@ratelimit(key="user", rate="10/m", block=True)
@require_POST
@login_required
def api_reserve(request, event_id):
    event = get_object_or_404(Event, pk=event_id, is_active=True)

    reservation, error = event.reserve(request.user)
    if error:
        return JsonResponse({"error": error}, status=400)

    return JsonResponse({
        "message": "Reservation confirmed!",
        "reservation_id": reservation.id,
        "spots_left": event.spots_left(),
    })


@ratelimit(key="user", rate="10/m", block=True)
@require_POST
@login_required
def api_cancel(request, event_id):
    reservation = get_object_or_404(
        Reservation, user=request.user, event_id=event_id, status="confirmed"
    )
    reservation.cancel()

    return JsonResponse({
        "message": "Reservation cancelled.",
        "spots_left": reservation.event.spots_left(),
    })


@ratelimit(key="user", rate="5/m", block=True)
@require_POST
@login_required
def api_review(request, event_id):
    event = get_object_or_404(Event, pk=event_id)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid data."}, status=400)

    form = ReviewForm(data)
    if not form.is_valid():
        first_error = next(iter(form.errors.values()))[0]
        return JsonResponse({"error": first_error}, status=400)

    review, error = event.add_review(
        user=request.user,
        rating=form.cleaned_data["rating"],
        comment=form.cleaned_data["comment"],
    )
    if error:
        return JsonResponse({"error": error}, status=400)

    serializer = ReviewSerializer(review)
    return JsonResponse({
        "message": "Review submitted!",
        "review": serializer.data,
        "average_rating": event.average_rating(),
    })


@ratelimit(key="user", rate="20/m", block=True)
@require_POST
@login_required
def api_toggle_favorite(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    favorited = event.toggle_favorite(request.user)
    return JsonResponse({"favorited": favorited})


@login_required
def api_notifications(request):
    unread_count = Notification.objects.filter(
        recipient=request.user, is_read=False
    ).count()
    latest = Notification.objects.filter(recipient=request.user)[:10]
    serializer = NotificationSerializer(latest, many=True)
    return JsonResponse({
        "unread_count": unread_count,
        "notifications": serializer.data,
    })


@require_POST
@login_required
def api_mark_read(request):
    Notification.objects.filter(
        recipient=request.user, is_read=False
    ).update(is_read=True)
    return JsonResponse({"message": "All notifications marked as read."})
