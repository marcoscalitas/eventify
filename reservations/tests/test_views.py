import json
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from rolepermissions.roles import assign_role

from ..models import Category, Event, Review, UserProfile
from ..services.booking import reserve


@override_settings(RATELIMIT_ENABLE=False)
class BruteViewValidationTests(TestCase):
    """Brute-force tests: bypass front-end, POST bad data directly to views."""

    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user("org", "org@t.com", "Test@1234")
        self.attendee = User.objects.create_user("att", "att@t.com", "Test@1234")
        assign_role(self.organizer, "organizer")
        assign_role(self.attendee, "attendee")
        UserProfile.objects.create(user=self.organizer)
        UserProfile.objects.create(user=self.attendee)
        self.category = Category.objects.create(name="Music")

    # ── Register view ────────────────────────────────────────

    def test_register_post_short_username_rejected(self):
        r = self.client.post(reverse("register"), {
            "username": "ab", "email": "a@b.com",
            "password": "Test@1234", "confirmation": "Test@1234", "role": "attendee",
        })
        self.assertEqual(r.status_code, 200)  # re-render with error
        self.assertFalse(User.objects.filter(username="ab").exists())

    def test_register_post_mismatch_passwords_rejected(self):
        r = self.client.post(reverse("register"), {
            "username": "newuser", "email": "a@b.com",
            "password": "Test@1234", "confirmation": "Diff@1234", "role": "attendee",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_register_post_invalid_role_rejected(self):
        r = self.client.post(reverse("register"), {
            "username": "newuser", "email": "a@b.com",
            "password": "Test@1234", "confirmation": "Test@1234", "role": "superadmin",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_register_post_bad_email_rejected(self):
        r = self.client.post(reverse("register"), {
            "username": "newuser", "email": "not-email",
            "password": "Test@1234", "confirmation": "Test@1234", "role": "attendee",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    def test_register_post_short_password_rejected(self):
        r = self.client.post(reverse("register"), {
            "username": "newuser", "email": "a@b.com",
            "password": "12345", "confirmation": "12345", "role": "attendee",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(User.objects.filter(username="newuser").exists())

    # ── Create event view ────────────────────────────────────

    def test_create_event_past_date_rejected(self):
        self.client.login(username="org", password="Test@1234")
        r = self.client.post(reverse("create_event"), {
            "title": "Past", "description": "desc", "venue": "Here",
            "start_date": (date.today() - timedelta(days=30)).isoformat(),
            "start_time": "20:00", "capacity": 10, "price": "0",
        })
        self.assertEqual(r.status_code, 200)  # re-render form
        self.assertFalse(Event.objects.filter(title="Past").exists())

    def test_create_event_zero_capacity_rejected(self):
        self.client.login(username="org", password="Test@1234")
        r = self.client.post(reverse("create_event"), {
            "title": "Zero", "description": "desc", "venue": "Here",
            "start_date": (date.today() + timedelta(days=7)).isoformat(),
            "start_time": "20:00", "capacity": 0, "price": "0",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Event.objects.filter(title="Zero").exists())

    def test_create_event_negative_capacity_rejected(self):
        self.client.login(username="org", password="Test@1234")
        r = self.client.post(reverse("create_event"), {
            "title": "Neg", "description": "desc", "venue": "Here",
            "start_date": (date.today() + timedelta(days=7)).isoformat(),
            "start_time": "20:00", "capacity": -1, "price": "0",
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Event.objects.filter(title="Neg").exists())

    def test_create_event_empty_title_rejected(self):
        self.client.login(username="org", password="Test@1234")
        r = self.client.post(reverse("create_event"), {
            "title": "", "description": "desc", "venue": "Here",
            "start_date": (date.today() + timedelta(days=7)).isoformat(),
            "start_time": "20:00", "capacity": 10, "price": "0",
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Event.objects.count(), 0)

    def test_create_event_without_image_ok(self):
        self.client.login(username="org", password="Test@1234")
        r = self.client.post(reverse("create_event"), {
            "title": "NoImg", "description": "desc", "venue": "Here",
            "start_date": (date.today() + timedelta(days=7)).isoformat(),
            "start_time": "20:00", "capacity": 10, "price": "0",
        })
        self.assertEqual(r.status_code, 302)
        self.assertTrue(Event.objects.filter(title="NoImg").exists())

    # ── Profile view ─────────────────────────────────────────

    def test_profile_post_invalid_email_rejected(self):
        self.client.login(username="att", password="Test@1234")
        r = self.client.post(reverse("profile"), {
            "first_name": "A", "last_name": "B",
            "email": "bad-email", "bio": "hi",
        })
        self.assertEqual(r.status_code, 200)
        self.attendee.refresh_from_db()
        self.assertNotEqual(self.attendee.email, "bad-email")

    def test_profile_post_bio_too_long_rejected(self):
        self.client.login(username="att", password="Test@1234")
        r = self.client.post(reverse("profile"), {
            "first_name": "A", "last_name": "B",
            "email": "ok@ok.com", "bio": "x" * 501,
        })
        self.assertEqual(r.status_code, 200)
        profile = UserProfile.objects.get(user=self.attendee)
        self.assertNotEqual(len(profile.bio), 501)

    def test_profile_post_valid_accepted(self):
        self.client.login(username="att", password="Test@1234")
        r = self.client.post(reverse("profile"), {
            "first_name": "John", "last_name": "Doe",
            "email": "john@doe.com", "bio": "My bio",
        })
        self.assertEqual(r.status_code, 302)  # redirect
        self.attendee.refresh_from_db()
        self.assertEqual(self.attendee.first_name, "John")

    # ── Review API ───────────────────────────────────────────

    def _make_event_and_reserve(self):
        event = Event.objects.create(
            title="Ev", description="D", category=self.category,
            organizer=self.organizer, venue="L",
            start_date=date.today() + timedelta(days=7),
            start_time=time(20, 0), capacity=10,
        )
        reserve(self.attendee, event)
        return event

    def test_review_api_rating_zero_rejected(self):
        event = self._make_event_and_reserve()
        self.client.login(username="att", password="Test@1234")
        r = self.client.post(
            reverse("api_review", args=[event.id]),
            json.dumps({"rating": 0, "comment": ""}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Review.objects.filter(event=event).exists())

    def test_review_api_rating_six_rejected(self):
        event = self._make_event_and_reserve()
        self.client.login(username="att", password="Test@1234")
        r = self.client.post(
            reverse("api_review", args=[event.id]),
            json.dumps({"rating": 6, "comment": ""}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_review_api_rating_negative_rejected(self):
        event = self._make_event_and_reserve()
        self.client.login(username="att", password="Test@1234")
        r = self.client.post(
            reverse("api_review", args=[event.id]),
            json.dumps({"rating": -1, "comment": ""}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_review_api_comment_too_long_rejected(self):
        event = self._make_event_and_reserve()
        self.client.login(username="att", password="Test@1234")
        r = self.client.post(
            reverse("api_review", args=[event.id]),
            json.dumps({"rating": 3, "comment": "x" * 1001}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_review_api_missing_rating_rejected(self):
        event = self._make_event_and_reserve()
        self.client.login(username="att", password="Test@1234")
        r = self.client.post(
            reverse("api_review", args=[event.id]),
            json.dumps({"comment": "no rating"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_review_api_invalid_json_rejected(self):
        event = self._make_event_and_reserve()
        self.client.login(username="att", password="Test@1234")
        r = self.client.post(
            reverse("api_review", args=[event.id]),
            "not json at all",
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)

    def test_review_api_valid_accepted(self):
        event = self._make_event_and_reserve()
        self.client.login(username="att", password="Test@1234")
        r = self.client.post(
            reverse("api_review", args=[event.id]),
            json.dumps({"rating": 4, "comment": "Nice"}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(Review.objects.filter(event=event, user=self.attendee).exists())

    def test_review_api_huge_rating_rejected(self):
        event = self._make_event_and_reserve()
        self.client.login(username="att", password="Test@1234")
        r = self.client.post(
            reverse("api_review", args=[event.id]),
            json.dumps({"rating": 999999, "comment": ""}),
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 400)


class PageViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.organizer = User.objects.create_user("organizer", "org@test.com", "Test@1234")
        self.attendee = User.objects.create_user("attendee", "att@test.com", "Test@1234")
        assign_role(self.attendee, "attendee")
        assign_role(self.organizer, "organizer")
        UserProfile.objects.create(user=self.attendee)
        UserProfile.objects.create(user=self.organizer)
        self.event = Event.objects.create(
            title="Concert",
            description="A great concert",
            organizer=self.organizer,
            venue="Lisbon",
            start_date=date.today() + timedelta(days=7),
            start_time=time(20, 0),
            capacity=5,
        )

    def test_index_page(self):
        response = self.client.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

    def test_event_detail_page(self):
        response = self.client.get(reverse("event_detail", args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Concert")

    def test_login_page(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)

    def test_register_page(self):
        response = self.client.get(reverse("register"))
        self.assertEqual(response.status_code, 200)

    def test_profile_requires_login(self):
        response = self.client.get(reverse("profile"))
        self.assertEqual(response.status_code, 302)

    def test_notifications_requires_login(self):
        response = self.client.get(reverse("notifications"))
        self.assertEqual(response.status_code, 302)

    def test_create_event_requires_organizer(self):
        self.client.login(username="attendee", password="Test@1234")
        response = self.client.get(reverse("create_event"))
        self.assertEqual(response.status_code, 403)

    def test_create_event_allowed_for_organizer(self):
        self.client.login(username="organizer", password="Test@1234")
        response = self.client.get(reverse("create_event"))
        self.assertEqual(response.status_code, 200)

    def test_my_events_requires_organizer(self):
        self.client.login(username="attendee", password="Test@1234")
        response = self.client.get(reverse("my_events"))
        self.assertEqual(response.status_code, 403)

    def test_public_profile(self):
        response = self.client.get(reverse("profile_public", args=["organizer"]))
        self.assertEqual(response.status_code, 200)

    def test_404_page(self):
        response = self.client.get("/nonexistent-page/")
        self.assertEqual(response.status_code, 404)
