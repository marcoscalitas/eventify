from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse

from .models import Notification


def notify(recipient, notification_type, title, message, link="", send_email=True):
    """Create an in-app notification and optionally send an email."""
    notification = Notification.objects.create(
        recipient=recipient,
        notification_type=notification_type,
        title=title,
        message=message,
        link=link,
    )

    if send_email and recipient.email:
        html_message = render_to_string("reservations/emails/notification.html", {
            "username": recipient.username,
            "title": title,
            "message": message,
            "link": link,
        })
        send_mail(
            subject=title,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient.email],
            html_message=html_message,
            fail_silently=True,
        )

    return notification


def notify_reservation_confirmed(user, event):
    event_url = reverse("event_detail", args=[event.id])
    notify(
        recipient=user,
        notification_type="reservation_confirmed",
        title=f"Reservation confirmed: {event.title}",
        message=f"Your spot at \"{event.title}\" on {event.date} at {event.time} has been confirmed. {event.spots_left()} spots remaining.",
        link=event_url,
    )
    notify(
        recipient=event.organizer,
        notification_type="reservation_confirmed",
        title=f"New reservation: {event.title}",
        message=f"{user.username} has reserved a spot at \"{event.title}\". {event.spots_left()} spots remaining.",
        link=event_url,
    )


def notify_reservation_cancelled(user, event):
    event_url = reverse("event_detail", args=[event.id])
    notify(
        recipient=user,
        notification_type="reservation_cancelled",
        title=f"Reservation cancelled: {event.title}",
        message=f"Your reservation for \"{event.title}\" has been cancelled.",
        link=event_url,
    )
    notify(
        recipient=event.organizer,
        notification_type="reservation_cancelled",
        title=f"Cancellation: {event.title}",
        message=f"{user.username} cancelled their reservation for \"{event.title}\". {event.spots_left()} spots now available.",
        link=event_url,
    )


def notify_new_review(reviewer, event, rating):
    event_url = reverse("event_detail", args=[event.id])
    notify(
        recipient=event.organizer,
        notification_type="new_review",
        title=f"New review: {event.title}",
        message=f"{reviewer.username} gave \"{event.title}\" a {rating}★ review.",
        link=event_url,
    )


def notify_event_updated(event):
    from .models import Reservation
    event_url = reverse("event_detail", args=[event.id])
    attendees = Reservation.objects.filter(
        event=event, status=Reservation.CONFIRMED
    ).select_related("user")

    for reservation in attendees:
        notify(
            recipient=reservation.user,
            notification_type="event_updated",
            title=f"Event updated: {event.title}",
            message=f"The event \"{event.title}\" has been updated by the organizer. Check the new details.",
            link=event_url,
        )
