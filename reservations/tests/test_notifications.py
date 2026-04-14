from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from ..models import Event, Notification
from ..services.booking import reserve


class NotificationTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user("organizer", "org@test.com", "Test@1234")
        self.attendee = User.objects.create_user("attendee", "att@test.com", "Test@1234")
        self.event = Event.objects.create(
            title="Concert",
            description="A great concert",
            organizer=self.organizer,
            venue="Lisbon",
            start_date=date.today() + timedelta(days=7),
            start_time=time(20, 0),
            capacity=10,
        )

    def test_reserve_creates_notifications(self):
        reserve(self.attendee, self.event)
        self.assertTrue(Notification.objects.filter(recipient=self.attendee).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.organizer).exists())

    def test_cancel_creates_notifications(self):
        reservation, _ = reserve(self.attendee, self.event)
        count_before = Notification.objects.count()
        reservation.cancel()
        self.assertGreater(Notification.objects.count(), count_before)
