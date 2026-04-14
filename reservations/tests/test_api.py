import json
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from rolepermissions.roles import assign_role

from ..models import Category, Event, Notification, Reservation, UserProfile


@override_settings(RATELIMIT_ENABLE=False)
class APITests(TestCase):
    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user("organizer", "org@test.com", "Test@1234")
        self.attendee = User.objects.create_user("attendee", "att@test.com", "Test@1234")
        assign_role(self.attendee, "attendee")
        assign_role(self.organizer, "organizer")
        UserProfile.objects.create(user=self.attendee)
        UserProfile.objects.create(user=self.organizer)
        self.category = Category.objects.create(name="Music")
        self.event = Event.objects.create(
            title="Concert",
            description="A great concert",
            category=self.category,
            organizer=self.organizer,
            location="Lisbon",
            date=date.today() + timedelta(days=7),
            time=time(20, 0),
            capacity=5,
        )

    def test_api_events_list(self):
        response = self.client.get(reverse("api_events"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["events"]), 1)
        self.assertEqual(data["events"][0]["title"], "Concert")

    def test_api_events_search(self):
        response = self.client.get(reverse("api_events"), {"search": "xyz"})
        data = response.json()
        self.assertEqual(len(data["events"]), 0)

    def test_api_events_filter_category(self):
        response = self.client.get(reverse("api_events"), {"category": "Music"})
        data = response.json()
        self.assertEqual(len(data["events"]), 1)

    def test_api_reserve_unauthenticated(self):
        response = self.client.post(reverse("api_reserve", args=[self.event.id]))
        self.assertIn(response.status_code, [302, 403])

    def test_api_reserve_success(self):
        self.client.login(username="attendee", password="Test@1234")
        response = self.client.post(reverse("api_reserve", args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["message"], "Reservation confirmed!")

    def test_api_reserve_duplicate(self):
        self.client.login(username="attendee", password="Test@1234")
        self.client.post(reverse("api_reserve", args=[self.event.id]))
        response = self.client.post(reverse("api_reserve", args=[self.event.id]))
        self.assertEqual(response.status_code, 400)

    def test_api_cancel_success(self):
        self.client.login(username="attendee", password="Test@1234")
        self.client.post(reverse("api_reserve", args=[self.event.id]))
        response = self.client.post(reverse("api_cancel", args=[self.event.id]))
        self.assertEqual(response.status_code, 200)

    def test_api_review_success(self):
        self.client.login(username="attendee", password="Test@1234")
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        response = self.client.post(
            reverse("api_review", args=[self.event.id]),
            data=json.dumps({"rating": 5, "comment": "Awesome!"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["review"]["rating"], 5)

    def test_api_review_no_reservation(self):
        self.client.login(username="attendee", password="Test@1234")
        response = self.client.post(
            reverse("api_review", args=[self.event.id]),
            data=json.dumps({"rating": 5, "comment": "Nope"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 400)

    def test_api_toggle_favorite(self):
        self.client.login(username="attendee", password="Test@1234")
        response = self.client.post(reverse("api_favorite", args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["favorited"])

        response = self.client.post(reverse("api_favorite", args=[self.event.id]))
        self.assertFalse(response.json()["favorited"])

    def test_api_notifications(self):
        self.client.login(username="attendee", password="Test@1234")
        response = self.client.get(reverse("api_notifications"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("unread_count", data)

    def test_api_mark_read(self):
        self.client.login(username="attendee", password="Test@1234")
        Notification.objects.create(
            recipient=self.attendee,
            notification_type="event_updated",
            title="Test",
            message="Test notification",
        )
        self.client.post(reverse("api_mark_read"))
        self.assertEqual(
            Notification.objects.filter(recipient=self.attendee, is_read=False).count(), 0
        )
