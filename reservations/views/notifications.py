from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from ..models import Notification


@login_required
def notifications(request):
    notifs = Notification.objects.filter(recipient=request.user)[:50]
    # Mark all as read when viewing the page
    Notification.objects.filter(recipient=request.user, read_at__isnull=True).update(read_at=timezone.now())
    return render(request, "reservations/notifications/notifications.html", {
        "notifications": notifs,
    })
