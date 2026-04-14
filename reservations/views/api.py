from django.shortcuts import get_object_or_404
from django.utils import timezone
from django_ratelimit.decorators import ratelimit
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import Event, Notification, Reservation
from ..forms import ReviewForm
from ..serializers import EventSerializer, ReviewSerializer, NotificationSerializer
from ..services.booking import reserve
from ..services.review import add_review
from ..services.favorite import toggle_favorite

EVENTS_PER_PAGE = 12


def first_form_error(form):
    return next(iter(form.errors.values()))[0]


def ratelimited_error(request, exception):
    return Response({"error": "Too many requests. Please slow down."}, status=429)


class EventListAPIView(APIView):
    """List events with optional search, category filter, and pagination."""

    @staticmethod
    def get(request):
        category = request.query_params.get("category", "")
        search = request.query_params.get("search", "")
        page = int(request.query_params.get("page", 1))

        events = Event.objects.filter(status=Event.PUBLISHED).select_related("category", "organizer")

        if category:
            events = events.filter(category__name=category)
        if search:
            events = events.filter(title__icontains=search)

        total = events.count()
        start = (page - 1) * EVENTS_PER_PAGE
        end = start + EVENTS_PER_PAGE
        page_events = events[start:end]

        serializer = EventSerializer(page_events, many=True, context={"truncate": True, "request": request})
        return Response({
            "events": serializer.data,
            "page": page,
            "total_pages": (total + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE,
            "total": total,
        })


class ReserveAPIView(APIView):
    """Reserve a spot for the authenticated user."""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request, event_id):
        event = get_object_or_404(Event, pk=event_id, status=Event.PUBLISHED)

        reservation, error = reserve(request.user, event)
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            "message": "Reservation confirmed!",
            "reservation_id": reservation.id,
            "spots_left": event.spots_left(),
        })


class CancelAPIView(APIView):
    """Cancel the authenticated user's reservation."""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request, event_id):
        reservation = get_object_or_404(
            Reservation, user=request.user, event_id=event_id, status=Reservation.CONFIRMED
        )
        reservation.cancel()

        return Response({
            "message": "Reservation cancelled.",
            "spots_left": reservation.event.spots_left(),
        })


class ReviewAPIView(APIView):
    """Submit a review for an event."""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request, event_id):
        event = get_object_or_404(Event, pk=event_id)

        form = ReviewForm(request.data)
        if not form.is_valid():
            return Response({"error": first_form_error(form)}, status=status.HTTP_400_BAD_REQUEST)

        review, error = add_review(
            user=request.user,
            event=event,
            rating=form.cleaned_data["rating"],
            comment=form.cleaned_data["comment"],
        )
        if error:
            return Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ReviewSerializer(review)
        return Response({
            "message": "Review submitted!",
            "review": serializer.data,
            "average_rating": event.average_rating(),
        })


class ToggleFavoriteAPIView(APIView):
    """Toggle favorite status for an event."""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request, event_id):
        event = get_object_or_404(Event, pk=event_id)
        favorited = toggle_favorite(request.user, event)
        return Response({"favorited": favorited})


class NotificationListAPIView(APIView):
    """List notifications for the authenticated user."""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def get(request):
        unread_count = Notification.objects.filter(
            recipient=request.user, read_at__isnull=True
        ).count()
        latest = Notification.objects.filter(recipient=request.user)[:10]
        serializer = NotificationSerializer(latest, many=True)
        return Response({
            "unread_count": unread_count,
            "notifications": serializer.data,
        })


class MarkReadAPIView(APIView):
    """Mark all notifications as read."""
    permission_classes = [IsAuthenticated]

    @staticmethod
    def post(request):
        Notification.objects.filter(
            recipient=request.user, read_at__isnull=True
        ).update(read_at=timezone.now())
        return Response({"message": "All notifications marked as read."})


# ── Function aliases for URL compatibility ───────────────────
api_events = EventListAPIView.as_view()
api_reserve = ReserveAPIView.as_view()
api_cancel = CancelAPIView.as_view()
api_review = ReviewAPIView.as_view()
api_toggle_favorite = ToggleFavoriteAPIView.as_view()
api_notifications = NotificationListAPIView.as_view()
api_mark_read = MarkReadAPIView.as_view()
