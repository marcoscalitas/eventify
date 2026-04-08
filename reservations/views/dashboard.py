import csv
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from ..models import Event, Reservation
from ..decorators import role_required


@role_required("organizer")
def my_events(request):
    events = Event.objects.filter(organizer=request.user).order_by("-date")
    event_stats = []
    for event in events:
        confirmed = event.reservations.filter(status="confirmed").count()
        event_stats.append({
            "event": event,
            "confirmed": confirmed,
            "spots_left": event.capacity - confirmed,
            "occupancy": round((confirmed / event.capacity) * 100) if event.capacity > 0 else 0,
        })
    return render(request, "reservations/dashboard/my_events.html", {
        "event_stats": event_stats,
    })


@role_required("organizer")
def attendees(request, event_id):
    event = get_object_or_404(Event, pk=event_id, organizer=request.user)
    reservations = event.reservations.filter(
        status="confirmed"
    ).select_related("user").order_by("created_at")
    return render(request, "reservations/dashboard/attendees.html", {
        "event": event,
        "reservations": reservations,
    })


@role_required("organizer")
def export_attendees_csv(request, event_id):
    event = get_object_or_404(Event, pk=event_id, organizer=request.user)
    reservations = event.reservations.filter(
        status="confirmed"
    ).select_related("user").order_by("created_at")

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{event.title}_attendees.csv"'

    writer = csv.writer(response)
    writer.writerow(["Username", "Email", "Reserved At"])
    for r in reservations:
        writer.writerow([r.user.username, r.user.email, r.created_at.strftime("%Y-%m-%d %H:%M")])

    return response
