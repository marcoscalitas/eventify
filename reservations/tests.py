import json
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from rolepermissions.roles import assign_role

from .models import Category, Event, Favorite, Notification, Reservation, Review, UserProfile


class EventModelTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user("organizer", "org@test.com", "Test@1234")
        self.attendee = User.objects.create_user("attendee", "att@test.com", "Test@1234")
        self.category = Category.objects.create(name="Music")
        self.event = Event.objects.create(
            title="Concert",
            description="A great concert",
            category=self.category,
            organizer=self.organizer,
            location="Lisbon",
            date=date.today() + timedelta(days=7),
            time=time(20, 0),
            capacity=2,
        )

    def test_spots_left(self):
        self.assertEqual(self.event.spots_left(), 2)
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        self.assertEqual(self.event.spots_left(), 1)

    def test_average_rating_none(self):
        self.assertIsNone(self.event.average_rating())

    def test_average_rating(self):
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        Review.objects.create(user=self.attendee, event=self.event, rating=4)
        self.assertEqual(self.event.average_rating(), 4.0)

    def test_reserve_success(self):
        reservation, error = self.event.reserve(self.attendee)
        self.assertIsNotNone(reservation)
        self.assertIsNone(error)
        self.assertEqual(reservation.status, "confirmed")
        self.assertEqual(self.event.spots_left(), 1)

    def test_reserve_duplicate(self):
        self.event.reserve(self.attendee)
        _, error = self.event.reserve(self.attendee)
        self.assertEqual(error, "Already reserved.")

    def test_reserve_full(self):
        user2 = User.objects.create_user("user2", "u2@test.com", "Test@1234")
        self.event.reserve(self.attendee)
        self.event.reserve(user2)
        user3 = User.objects.create_user("user3", "u3@test.com", "Test@1234")
        _, error = self.event.reserve(user3)
        self.assertEqual(error, "No spots available.")

    def test_add_review_success(self):
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        review, error = self.event.add_review(self.attendee, 5, "Great!")
        self.assertIsNotNone(review)
        self.assertIsNone(error)
        self.assertEqual(review.rating, 5)

    def test_add_review_no_reservation(self):
        _, error = self.event.add_review(self.attendee, 5, "Great!")
        self.assertEqual(error, "You must have a reservation to review.")

    def test_add_review_duplicate(self):
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        self.event.add_review(self.attendee, 5, "Great!")
        _, error = self.event.add_review(self.attendee, 4, "Again")
        self.assertEqual(error, "You already reviewed this event.")

    def test_toggle_favorite(self):
        result = self.event.toggle_favorite(self.attendee)
        self.assertTrue(result)
        self.assertTrue(Favorite.objects.filter(user=self.attendee, event=self.event).exists())

        result = self.event.toggle_favorite(self.attendee)
        self.assertFalse(result)
        self.assertFalse(Favorite.objects.filter(user=self.attendee, event=self.event).exists())


class ReservationModelTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user("organizer", "org@test.com", "Test@1234")
        self.attendee = User.objects.create_user("attendee", "att@test.com", "Test@1234")
        self.event = Event.objects.create(
            title="Concert",
            description="A great concert",
            organizer=self.organizer,
            location="Lisbon",
            date=date.today() + timedelta(days=7),
            time=time(20, 0),
            capacity=10,
        )

    def test_cancel(self):
        reservation, _ = self.event.reserve(self.attendee)
        reservation.cancel()
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, "cancelled")


class NotificationTests(TestCase):
    def setUp(self):
        self.organizer = User.objects.create_user("organizer", "org@test.com", "Test@1234")
        self.attendee = User.objects.create_user("attendee", "att@test.com", "Test@1234")
        self.event = Event.objects.create(
            title="Concert",
            description="A great concert",
            organizer=self.organizer,
            location="Lisbon",
            date=date.today() + timedelta(days=7),
            time=time(20, 0),
            capacity=10,
        )

    def test_reserve_creates_notifications(self):
        self.event.reserve(self.attendee)
        self.assertTrue(Notification.objects.filter(recipient=self.attendee).exists())
        self.assertTrue(Notification.objects.filter(recipient=self.organizer).exists())

    def test_cancel_creates_notifications(self):
        reservation, _ = self.event.reserve(self.attendee)
        count_before = Notification.objects.count()
        reservation.cancel()
        self.assertGreater(Notification.objects.count(), count_before)


class FormTests(TestCase):
    def test_register_form_passwords_mismatch(self):
        from .forms import RegisterForm
        form = RegisterForm(data={
            "username": "newuser",
            "email": "new@test.com",
            "password": "Test@1234",
            "confirmation": "Diff@1234",
            "role": "attendee",
        })
        self.assertFalse(form.is_valid())

    def test_register_form_valid(self):
        from .forms import RegisterForm
        form = RegisterForm(data={
            "username": "newuser",
            "email": "new@test.com",
            "password": "Test@1234",
            "confirmation": "Test@1234",
            "role": "attendee",
        })
        self.assertTrue(form.is_valid())

    def test_event_form_invalid_capacity(self):
        from .forms import EventForm
        category = Category.objects.create(name="Music")
        form = EventForm(data={
            "title": "Test",
            "description": "Desc",
            "category": category.id,
            "location": "Lisbon",
            "date": date.today() + timedelta(days=7),
            "time": "20:00",
            "capacity": 0,
        })
        self.assertFalse(form.is_valid())

    def test_review_form_valid(self):
        from .forms import ReviewForm
        form = ReviewForm(data={"rating": 5, "comment": "Great!"})
        self.assertTrue(form.is_valid())


class BruteFormValidationTests(TestCase):
    """Brute-force validation tests for every form field boundary."""

    # ── LoginForm ────────────────────────────────────────────

    def test_login_empty_email(self):
        from .forms import LoginForm
        form = LoginForm(data={"email": "", "password": "Test@1234"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_login_empty_password(self):
        from .forms import LoginForm
        form = LoginForm(data={"email": "user@test.com", "password": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    def test_login_both_empty(self):
        from .forms import LoginForm
        form = LoginForm(data={"email": "", "password": ""})
        self.assertFalse(form.is_valid())

    def test_login_missing_fields(self):
        from .forms import LoginForm
        form = LoginForm(data={})
        self.assertFalse(form.is_valid())

    def test_login_invalid_email(self):
        from .forms import LoginForm
        form = LoginForm(data={"email": "not-an-email", "password": "Test@1234"})
        self.assertFalse(form.is_valid())

    def test_login_valid(self):
        from .forms import LoginForm
        form = LoginForm(data={"email": "user@test.com", "password": "Test@1234"})
        self.assertTrue(form.is_valid())

    # ── RegisterForm ─────────────────────────────────────────

    def _register_data(self, **overrides):
        data = {
            "username": "newuser",
            "email": "new@test.com",
            "password": "Test@1234",
            "confirmation": "Test@1234",
            "role": "attendee",
        }
        data.update(overrides)
        return data

    def test_register_username_too_short(self):
        from .forms import RegisterForm
        form = RegisterForm(data=self._register_data(username="ab"))
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_register_username_exactly_3(self):
        from .forms import RegisterForm
        form = RegisterForm(data=self._register_data(username="abc"))
        self.assertTrue(form.is_valid())

    def test_register_username_too_long(self):
        from .forms import RegisterForm
        form = RegisterForm(data=self._register_data(username="a" * 151))
        self.assertFalse(form.is_valid())

    def test_register_username_exactly_150(self):
        from .forms import RegisterForm
        form = RegisterForm(data=self._register_data(username="a" * 150))
        self.assertTrue(form.is_valid())

    def test_register_username_taken(self):
        from .forms import RegisterForm
        User.objects.create_user("taken", "t@t.com", "Test@1234")
        form = RegisterForm(data=self._register_data(username="taken"))
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_register_empty_email(self):
        from .forms import RegisterForm
        form = RegisterForm(data=self._register_data(email=""))
        self.assertFalse(form.is_valid())

    def test_register_invalid_email(self):
        from .forms import RegisterForm
        form = RegisterForm(data=self._register_data(email="not-an-email"))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_register_password_too_short(self):
        from .forms import RegisterForm
        form = RegisterForm(data=self._register_data(
            password="12345", confirmation="12345"
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    def test_register_password_exactly_8(self):
        from .forms import RegisterForm
        form = RegisterForm(data=self._register_data(
            password="Test@123", confirmation="Test@123"
        ))
        self.assertTrue(form.is_valid())

    def test_register_passwords_mismatch(self):
        from .forms import RegisterForm
        form = RegisterForm(data=self._register_data(confirmation="Wrong@1234"))
        self.assertFalse(form.is_valid())

    def test_register_invalid_role(self):
        from .forms import RegisterForm
        form = RegisterForm(data=self._register_data(role="admin"))
        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)

    def test_register_empty_role(self):
        from .forms import RegisterForm
        form = RegisterForm(data=self._register_data(role=""))
        self.assertFalse(form.is_valid())

    # ── EventForm ────────────────────────────────────────────

    def _event_data(self, **overrides):
        if not hasattr(self, "_cat"):
            self._cat = Category.objects.create(name="TestCat")
        data = {
            "title": "My Event",
            "description": "A description",
            "category": self._cat.id,
            "location": "Lisbon",
            "date": (date.today() + timedelta(days=7)).isoformat(),
            "time": "20:00",
            "capacity": 10,
        }
        data.update(overrides)
        return data

    def test_event_valid(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data())
        self.assertTrue(form.is_valid())

    def test_event_empty_title(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(title=""))
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_event_title_max_length(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(title="a" * 201))
        self.assertFalse(form.is_valid())

    def test_event_title_exactly_200(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(title="a" * 200))
        self.assertTrue(form.is_valid())

    def test_event_empty_description(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(description=""))
        self.assertFalse(form.is_valid())

    def test_event_empty_location(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(location=""))
        self.assertFalse(form.is_valid())

    def test_event_location_max_length(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(location="x" * 256))
        self.assertFalse(form.is_valid())

    def test_event_date_in_past(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(
            date=(date.today() - timedelta(days=1)).isoformat()
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("date", form.errors)

    def test_event_date_today(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(date=date.today().isoformat()))
        self.assertTrue(form.is_valid())

    def test_event_date_far_past(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(date="2020-01-01"))
        self.assertFalse(form.is_valid())

    def test_event_empty_date(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(date=""))
        self.assertFalse(form.is_valid())

    def test_event_invalid_date_format(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(date="not-a-date"))
        self.assertFalse(form.is_valid())

    def test_event_empty_time(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(time=""))
        self.assertFalse(form.is_valid())

    def test_event_capacity_zero(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(capacity=0))
        self.assertFalse(form.is_valid())
        self.assertIn("capacity", form.errors)

    def test_event_capacity_negative(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(capacity=-5))
        self.assertFalse(form.is_valid())

    def test_event_capacity_one(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data(capacity=1))
        self.assertTrue(form.is_valid())

    def test_event_no_category_ok(self):
        from .forms import EventForm
        data = self._event_data()
        data.pop("category")
        form = EventForm(data=data)
        self.assertTrue(form.is_valid())

    def test_event_no_image_ok(self):
        from .forms import EventForm
        form = EventForm(data=self._event_data())
        self.assertTrue(form.is_valid())

    # ── ProfileForm ──────────────────────────────────────────

    def test_profile_all_empty_is_valid(self):
        from .forms import ProfileForm
        form = ProfileForm(data={
            "first_name": "", "last_name": "", "email": "", "bio": "",
        })
        self.assertTrue(form.is_valid())

    def test_profile_invalid_email(self):
        from .forms import ProfileForm
        form = ProfileForm(data={
            "first_name": "", "last_name": "", "email": "bad", "bio": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_profile_first_name_too_long(self):
        from .forms import ProfileForm
        form = ProfileForm(data={
            "first_name": "a" * 151, "last_name": "", "email": "", "bio": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("first_name", form.errors)

    def test_profile_last_name_too_long(self):
        from .forms import ProfileForm
        form = ProfileForm(data={
            "first_name": "", "last_name": "a" * 151, "email": "", "bio": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("last_name", form.errors)

    def test_profile_bio_max_length(self):
        from .forms import ProfileForm
        form = ProfileForm(data={
            "first_name": "", "last_name": "", "email": "",
            "bio": "x" * 501,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("bio", form.errors)

    def test_profile_bio_exactly_500(self):
        from .forms import ProfileForm
        form = ProfileForm(data={
            "first_name": "", "last_name": "", "email": "",
            "bio": "x" * 500,
        })
        self.assertTrue(form.is_valid())

    # ── ReviewForm ───────────────────────────────────────────

    def test_review_rating_zero(self):
        from .forms import ReviewForm
        form = ReviewForm(data={"rating": 0, "comment": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)

    def test_review_rating_negative(self):
        from .forms import ReviewForm
        form = ReviewForm(data={"rating": -1, "comment": ""})
        self.assertFalse(form.is_valid())

    def test_review_rating_six(self):
        from .forms import ReviewForm
        form = ReviewForm(data={"rating": 6, "comment": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)

    def test_review_rating_missing(self):
        from .forms import ReviewForm
        form = ReviewForm(data={"comment": "hi"})
        self.assertFalse(form.is_valid())

    def test_review_rating_one(self):
        from .forms import ReviewForm
        form = ReviewForm(data={"rating": 1, "comment": ""})
        self.assertTrue(form.is_valid())

    def test_review_rating_five(self):
        from .forms import ReviewForm
        form = ReviewForm(data={"rating": 5, "comment": ""})
        self.assertTrue(form.is_valid())

    def test_review_comment_too_long(self):
        from .forms import ReviewForm
        form = ReviewForm(data={"rating": 3, "comment": "x" * 1001})
        self.assertFalse(form.is_valid())
        self.assertIn("comment", form.errors)

    def test_review_comment_exactly_1000(self):
        from .forms import ReviewForm
        form = ReviewForm(data={"rating": 3, "comment": "x" * 1000})
        self.assertTrue(form.is_valid())

    def test_review_empty_comment_ok(self):
        from .forms import ReviewForm
        form = ReviewForm(data={"rating": 4})
        self.assertTrue(form.is_valid())


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
            "title": "Past", "description": "desc", "location": "Here",
            "date": (date.today() - timedelta(days=30)).isoformat(),
            "time": "20:00", "capacity": 10,
        })
        self.assertEqual(r.status_code, 200)  # re-render form
        self.assertFalse(Event.objects.filter(title="Past").exists())

    def test_create_event_zero_capacity_rejected(self):
        self.client.login(username="org", password="Test@1234")
        r = self.client.post(reverse("create_event"), {
            "title": "Zero", "description": "desc", "location": "Here",
            "date": (date.today() + timedelta(days=7)).isoformat(),
            "time": "20:00", "capacity": 0,
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Event.objects.filter(title="Zero").exists())

    def test_create_event_negative_capacity_rejected(self):
        self.client.login(username="org", password="Test@1234")
        r = self.client.post(reverse("create_event"), {
            "title": "Neg", "description": "desc", "location": "Here",
            "date": (date.today() + timedelta(days=7)).isoformat(),
            "time": "20:00", "capacity": -1,
        })
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Event.objects.filter(title="Neg").exists())

    def test_create_event_empty_title_rejected(self):
        self.client.login(username="org", password="Test@1234")
        r = self.client.post(reverse("create_event"), {
            "title": "", "description": "desc", "location": "Here",
            "date": (date.today() + timedelta(days=7)).isoformat(),
            "time": "20:00", "capacity": 10,
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Event.objects.count(), 0)

    def test_create_event_without_image_ok(self):
        self.client.login(username="org", password="Test@1234")
        r = self.client.post(reverse("create_event"), {
            "title": "NoImg", "description": "desc", "location": "Here",
            "date": (date.today() + timedelta(days=7)).isoformat(),
            "time": "20:00", "capacity": 10,
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
            organizer=self.organizer, location="L",
            date=date.today() + timedelta(days=7),
            time=time(20, 0), capacity=10,
        )
        event.reserve(self.attendee)
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
        self.assertEqual(response.status_code, 302)

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
            location="Lisbon",
            date=date.today() + timedelta(days=7),
            time=time(20, 0),
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


class AuthTests(TestCase):
    def setUp(self):
        self.client = Client()

    def test_register_and_login(self):
        response = self.client.post(reverse("register"), {
            "username": "newuser",
            "email": "new@test.com",
            "password": "Test@1234",
            "confirmation": "Test@1234",
            "role": "attendee",
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_duplicate_username(self):
        User.objects.create_user("taken", "t@test.com", "Test@1234")
        response = self.client.post(reverse("register"), {
            "username": "taken",
            "email": "new@test.com",
            "password": "Test@1234",
            "confirmation": "Test@1234",
            "role": "attendee",
        })
        self.assertEqual(response.status_code, 200)

    def test_login_success(self):
        User.objects.create_user("testuser", "t@test.com", "Test@1234")
        response = self.client.post(reverse("login"), {
            "email": "t@test.com",
            "password": "Test@1234",
        })
        self.assertEqual(response.status_code, 302)

    def test_login_failure(self):
        response = self.client.post(reverse("login"), {
            "email": "nobody@test.com",
            "password": "Wrong@1234",
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid")

    def test_logout(self):
        User.objects.create_user("testuser", "t@test.com", "Test@1234")
        self.client.login(username="testuser", password="Test@1234")
        response = self.client.get(reverse("logout"))
        self.assertEqual(response.status_code, 302)


class EndToEndOrganizerTests(TestCase):
    """Full organizer journey: register → create event → edit → dashboard → attendees → CSV."""

    def test_organizer_full_journey(self):
        c = Client()

        # 1. Register as organizer
        response = c.post(reverse("register"), {
            "username": "org_e2e",
            "email": "org_e2e@test.com",
            "password": "Secure@123",
            "confirmation": "Secure@123",
            "role": "organizer",
        })
        self.assertEqual(response.status_code, 302)
        user = User.objects.get(username="org_e2e")
        self.assertTrue(UserProfile.objects.filter(user=user).exists())

        # 2. Create a category (needed for event)
        cat = Category.objects.create(name="Tech")

        # 3. Create event
        future = date.today() + timedelta(days=14)
        response = c.post(reverse("create_event"), {
            "title": "Django Workshop",
            "description": "Learn Django end to end",
            "category": cat.id,
            "location": "Porto",
            "date": future.isoformat(),
            "time": "10:00",
            "capacity": 30,
        })
        self.assertEqual(response.status_code, 302)
        event = Event.objects.get(title="Django Workshop")
        self.assertEqual(event.organizer, user)
        self.assertEqual(event.capacity, 30)

        # 4. Edit event — change capacity
        response = c.post(reverse("edit_event", args=[event.id]), {
            "title": "Django Workshop v2",
            "description": "Updated description",
            "category": cat.id,
            "location": "Porto",
            "date": future.isoformat(),
            "time": "10:00",
            "capacity": 50,
        })
        self.assertEqual(response.status_code, 302)
        event.refresh_from_db()
        self.assertEqual(event.title, "Django Workshop v2")
        self.assertEqual(event.capacity, 50)

        # 5. View organizer dashboard
        response = c.get(reverse("my_events"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django Workshop v2")

        # 6. View event detail as organizer
        response = c.get(reverse("event_detail", args=[event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Django Workshop v2")

        # 7. Create an attendee who reserves
        att = User.objects.create_user("att_e2e", "att@test.com", "Test@1234")
        assign_role(att, "attendee")
        UserProfile.objects.create(user=att)
        reservation, err = event.reserve(att)
        self.assertIsNone(err)

        # 8. View attendees page
        response = c.get(reverse("attendees", args=[event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "att_e2e")

        # 9. Export CSV
        response = c.get(reverse("export_csv", args=[event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode()
        self.assertIn("att_e2e", content)
        self.assertIn("att@test.com", content)

    def test_organizer_cannot_access_others_event(self):
        """Organizer A can't view attendees or edit Organizer B's event."""
        c = Client()

        # Organizer A
        org_a = User.objects.create_user("org_a", "a@test.com", "Test@1234")
        assign_role(org_a, "organizer")
        UserProfile.objects.create(user=org_a)

        # Organizer B creates event
        org_b = User.objects.create_user("org_b", "b@test.com", "Test@1234")
        assign_role(org_b, "organizer")
        UserProfile.objects.create(user=org_b)
        event = Event.objects.create(
            title="B's Event", description="Owned by B",
            organizer=org_b, location="Lisbon",
            date=date.today() + timedelta(days=7),
            time=time(20, 0), capacity=10,
        )

        # Organizer A tries to access B's attendees/CSV
        c.login(username="org_a", password="Test@1234")
        response = c.get(reverse("attendees", args=[event.id]))
        self.assertEqual(response.status_code, 404)

        response = c.get(reverse("export_csv", args=[event.id]))
        self.assertEqual(response.status_code, 404)


@override_settings(RATELIMIT_ENABLE=False)
class EndToEndAttendeeTests(TestCase):
    """Full attendee journey: register → browse → reserve → review → favorite → cancel."""

    def setUp(self):
        self.organizer = User.objects.create_user("org", "org@test.com", "Test@1234")
        assign_role(self.organizer, "organizer")
        UserProfile.objects.create(user=self.organizer)
        self.category = Category.objects.create(name="Music")
        self.event = Event.objects.create(
            title="Jazz Night",
            description="Live jazz",
            category=self.category,
            organizer=self.organizer,
            location="Lisbon",
            date=date.today() + timedelta(days=10),
            time=time(21, 0),
            capacity=3,
        )

    def test_attendee_full_journey(self):
        c = Client()

        # 1. Register as attendee
        c.post(reverse("register"), {
            "username": "jazz_fan",
            "email": "fan@test.com",
            "password": "Jazz@1234",
            "confirmation": "Jazz@1234",
            "role": "attendee",
        })
        user = User.objects.get(username="jazz_fan")

        # 2. Browse events via homepage
        response = c.get(reverse("index"))
        self.assertEqual(response.status_code, 200)

        # 3. Search events via API
        response = c.get(reverse("api_events"), {"search": "Jazz"})
        data = response.json()
        self.assertEqual(len(data["events"]), 1)
        self.assertEqual(data["events"][0]["title"], "Jazz Night")

        # 4. Filter by category
        response = c.get(reverse("api_events"), {"category": "Music"})
        data = response.json()
        self.assertEqual(len(data["events"]), 1)

        # 5. View event detail
        response = c.get(reverse("event_detail", args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jazz Night")

        # 6. Reserve spot
        response = c.post(reverse("api_reserve", args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Reservation confirmed!")
        self.assertEqual(self.event.spots_left(), 2)

        # 7. Check notifications — reservation confirmed
        response = c.get(reverse("api_notifications"))
        data = response.json()
        self.assertGreater(data["unread_count"], 0)

        # 8. View my reservations page
        response = c.get(reverse("my_reservations"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jazz Night")

        # 9. Submit a review
        response = c.post(
            reverse("api_review", args=[self.event.id]),
            data=json.dumps({"rating": 5, "comment": "Amazing!"}),
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["review"]["rating"], 5)

        # Verify average rating updated
        self.assertEqual(self.event.average_rating(), 5.0)

        # 10. Toggle favorite ON
        response = c.post(reverse("api_favorite", args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["favorited"])

        # 11. View favorites page
        response = c.get(reverse("my_favorites"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Jazz Night")

        # 12. Toggle favorite OFF
        response = c.post(reverse("api_favorite", args=[self.event.id]))
        self.assertFalse(response.json()["favorited"])

        # 13. Cancel reservation
        response = c.post(reverse("api_cancel", args=[self.event.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.event.spots_left(), 3)

        # 14. Mark notifications as read
        response = c.post(reverse("api_mark_read"))
        self.assertEqual(response.status_code, 200)
        notifs = Notification.objects.filter(recipient=user, is_read=False)
        self.assertEqual(notifs.count(), 0)

        # 15. View public organizer profile
        response = c.get(reverse("profile_public", args=["org"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "org")

    def test_attendee_cannot_access_organizer_pages(self):
        c = Client()
        att = User.objects.create_user("att_rbac", "rbac@test.com", "Test@1234")
        assign_role(att, "attendee")
        UserProfile.objects.create(user=att)
        c.login(username="att_rbac", password="Test@1234")

        # All organizer-only pages should return 403
        self.assertEqual(c.get(reverse("create_event")).status_code, 403)
        self.assertEqual(c.get(reverse("my_events")).status_code, 403)
        self.assertEqual(c.get(reverse("attendees", args=[self.event.id])).status_code, 403)
        self.assertEqual(c.get(reverse("export_csv", args=[self.event.id])).status_code, 403)


@override_settings(RATELIMIT_ENABLE=False)
class EndToEndCapacityTests(TestCase):
    """Tests the full reservation flow when capacity is reached."""

    def setUp(self):
        self.org = User.objects.create_user("org", "org@test.com", "Test@1234")
        assign_role(self.org, "organizer")
        UserProfile.objects.create(user=self.org)
        self.event = Event.objects.create(
            title="Small Workshop",
            description="Only 2 spots",
            organizer=self.org,
            location="Faro",
            date=date.today() + timedelta(days=5),
            time=time(14, 0),
            capacity=2,
        )

    def test_capacity_exhaustion_and_recovery(self):
        """Fill all spots, fail to reserve, cancel one, reserve again."""
        # Two attendees fill the event
        att1 = User.objects.create_user("att1", "a1@test.com", "Test@1234")
        att2 = User.objects.create_user("att2", "a2@test.com", "Test@1234")
        att3 = User.objects.create_user("att3", "a3@test.com", "Test@1234")
        for u in [att1, att2, att3]:
            assign_role(u, "attendee")
            UserProfile.objects.create(user=u)

        c1, c2, c3 = Client(), Client(), Client()
        c1.login(username="att1", password="Test@1234")
        c2.login(username="att2", password="Test@1234")
        c3.login(username="att3", password="Test@1234")

        # att1 reserves — success
        r = c1.post(reverse("api_reserve", args=[self.event.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.event.spots_left(), 1)

        # att2 reserves — success (last spot)
        r = c2.post(reverse("api_reserve", args=[self.event.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.event.spots_left(), 0)

        # att3 tries — fails, no spots
        r = c3.post(reverse("api_reserve", args=[self.event.id]))
        self.assertEqual(r.status_code, 400)
        self.assertIn("No spots", r.json()["error"])

        # API also reflects 0 spots
        r = c3.get(reverse("api_events"))
        ev = r.json()["events"][0]
        self.assertEqual(ev["spots_left"], 0)

        # att1 cancels — frees a spot
        r = c1.post(reverse("api_cancel", args=[self.event.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.event.spots_left(), 1)

        # att3 can now reserve
        r = c3.post(reverse("api_reserve", args=[self.event.id]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.event.spots_left(), 0)

    def test_duplicate_reserve_returns_error(self):
        att = User.objects.create_user("dup", "dup@test.com", "Test@1234")
        assign_role(att, "attendee")
        UserProfile.objects.create(user=att)
        c = Client()
        c.login(username="dup", password="Test@1234")

        r = c.post(reverse("api_reserve", args=[self.event.id]))
        self.assertEqual(r.status_code, 200)

        r = c.post(reverse("api_reserve", args=[self.event.id]))
        self.assertEqual(r.status_code, 400)
        self.assertIn("Already", r.json()["error"])


@override_settings(RATELIMIT_ENABLE=False)
class EndToEndNotificationFlowTests(TestCase):
    """Tests that all actions produce correct notifications for all parties."""

    def setUp(self):
        self.org = User.objects.create_user("org_nf", "org@test.com", "Test@1234")
        assign_role(self.org, "organizer")
        UserProfile.objects.create(user=self.org)
        self.att = User.objects.create_user("att_nf", "att@test.com", "Test@1234")
        assign_role(self.att, "attendee")
        UserProfile.objects.create(user=self.att)
        self.event = Event.objects.create(
            title="Notification Test Event",
            description="Testing notifs",
            organizer=self.org,
            location="Braga",
            date=date.today() + timedelta(days=5),
            time=time(18, 0),
            capacity=10,
        )
        self.c_att = Client()
        self.c_att.login(username="att_nf", password="Test@1234")
        self.c_org = Client()
        self.c_org.login(username="org_nf", password="Test@1234")

    def test_reserve_notifies_both_parties(self):
        r = self.c_att.post(reverse("api_reserve", args=[self.event.id]))
        self.assertEqual(r.status_code, 200)

        # Attendee gets notification
        self.assertTrue(
            Notification.objects.filter(recipient=self.att, is_read=False).exists()
        )

        # Organizer gets notification
        self.assertTrue(
            Notification.objects.filter(recipient=self.org, is_read=False).exists()
        )

    def test_cancel_notifies_both_parties(self):
        self.c_att.post(reverse("api_reserve", args=[self.event.id]))
        # Clear existing
        Notification.objects.all().update(is_read=True)

        self.c_att.post(reverse("api_cancel", args=[self.event.id]))

        att_notifs = Notification.objects.filter(recipient=self.att, is_read=False)
        org_notifs = Notification.objects.filter(recipient=self.org, is_read=False)
        self.assertTrue(att_notifs.exists())
        self.assertTrue(org_notifs.exists())

    def test_review_notifies_organizer(self):
        Reservation.objects.create(user=self.att, event=self.event, status="confirmed")
        Notification.objects.all().delete()

        self.c_att.post(
            reverse("api_review", args=[self.event.id]),
            data=json.dumps({"rating": 4, "comment": "Nice"}),
            content_type="application/json",
        )

        org_notifs = Notification.objects.filter(recipient=self.org)
        self.assertTrue(org_notifs.exists())
        self.assertTrue(any("review" in n.notification_type for n in org_notifs))

    def test_notifications_page_shows_all(self):
        self.c_att.post(reverse("api_reserve", args=[self.event.id]))
        response = self.c_att.get(reverse("notifications"))
        self.assertEqual(response.status_code, 200)

    def test_mark_read_clears_all(self):
        self.c_att.post(reverse("api_reserve", args=[self.event.id]))
        self.c_att.post(reverse("api_mark_read"))
        r = self.c_att.get(reverse("api_notifications"))
        self.assertEqual(r.json()["unread_count"], 0)


class EndToEndProfileTests(TestCase):
    """Tests profile edit and public profile viewing."""

    def test_edit_profile_and_view_public(self):
        c = Client()
        c.post(reverse("register"), {
            "username": "profile_user",
            "email": "prof@test.com",
            "password": "Profile@1",
            "confirmation": "Profile@1",
            "role": "attendee",
        })

        # Edit profile
        response = c.post(reverse("profile"), {
            "first_name": "Marco",
            "last_name": "Silva",
            "email": "updated@test.com",
            "bio": "I love events!",
        })
        self.assertEqual(response.status_code, 302)

        user = User.objects.get(username="profile_user")
        self.assertEqual(user.first_name, "Marco")
        self.assertEqual(user.last_name, "Silva")
        self.assertEqual(user.profile.bio, "I love events!")

        # View own profile page
        response = c.get(reverse("profile"))
        self.assertEqual(response.status_code, 200)

        # Another user views the public profile
        c2 = Client()
        response = c2.get(reverse("profile_public", args=["profile_user"]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "profile_user")


@override_settings(RATELIMIT_ENABLE=False)
class EndToEndSearchAndFilterTests(TestCase):
    """Tests event search, category filter, and pagination via the API."""

    def setUp(self):
        org = User.objects.create_user("org_sf", "org@test.com", "Test@1234")
        cat1 = Category.objects.create(name="Sports")
        cat2 = Category.objects.create(name="Technology")
        base_date = date.today() + timedelta(days=5)

        for i in range(15):
            Event.objects.create(
                title=f"Sports Event {i}" if i < 10 else f"Tech Talk {i}",
                description=f"Description {i}",
                category=cat1 if i < 10 else cat2,
                organizer=org,
                location="Lisbon",
                date=base_date + timedelta(days=i),
                time=time(10, 0),
                capacity=50,
            )

    def test_search_filters_correctly(self):
        c = Client()
        r = c.get(reverse("api_events"), {"search": "Tech Talk"})
        data = r.json()
        self.assertEqual(len(data["events"]), 5)
        self.assertTrue(all("Tech" in e["title"] for e in data["events"]))

    def test_category_filter(self):
        c = Client()
        r = c.get(reverse("api_events"), {"category": "Sports"})
        data = r.json()
        self.assertEqual(len(data["events"]), 10)

    def test_pagination(self):
        c = Client()
        r1 = c.get(reverse("api_events"), {"page": 1})
        d1 = r1.json()
        self.assertIn("total_pages", d1)
        self.assertGreater(d1["total_pages"], 1)

        r2 = c.get(reverse("api_events"), {"page": 2})
        d2 = r2.json()
        ids_p1 = {e["id"] for e in d1["events"]}
        ids_p2 = {e["id"] for e in d2["events"]}
        self.assertEqual(len(ids_p1 & ids_p2), 0)  # No overlap

    def test_empty_search(self):
        c = Client()
        r = c.get(reverse("api_events"), {"search": "nonexistent_xyz"})
        self.assertEqual(len(r.json()["events"]), 0)

    def test_combined_search_and_category(self):
        c = Client()
        r = c.get(reverse("api_events"), {"search": "Event", "category": "Sports"})
        data = r.json()
        self.assertTrue(all("Sports" == e.get("category") or "Event" in e["title"]
                            for e in data["events"]))


# ==========================================================================
# AJAX Auth Tests — JSON responses for frontend AJAX submissions
# ==========================================================================
class AjaxAuthTests(TestCase):
    AJAX_HEADERS = {"HTTP_ACCEPT": "application/json"}

    def setUp(self):
        self.user = User.objects.create_user("testuser", "test@test.com", "Test@1234")
        UserProfile.objects.create(user=self.user)

    # ---- Login AJAX ----

    def test_login_ajax_success(self):
        r = self.client.post(reverse("login"), {
            "email": "test@test.com",
            "password": "Test@1234",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("redirect", data)
        self.assertEqual(data["redirect"], "/")

    def test_login_ajax_invalid_credentials(self):
        r = self.client.post(reverse("login"), {
            "email": "test@test.com",
            "password": "Wrong@1234",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("error", data)
        self.assertIn("Invalid", data["error"])

    def test_login_ajax_empty_fields(self):
        r = self.client.post(reverse("login"), {
            "email": "",
            "password": "",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("error", data)

    def test_login_ajax_missing_password(self):
        r = self.client.post(reverse("login"), {
            "email": "test@test.com",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("error", data)

    def test_login_non_ajax_still_renders_html(self):
        r = self.client.post(reverse("login"), {
            "email": "test@test.com",
            "password": "Wrong@1234",
        })
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Invalid")
        self.assertEqual(r["Content-Type"], "text/html; charset=utf-8")

    def test_login_ajax_returns_json_content_type(self):
        r = self.client.post(reverse("login"), {
            "email": "test@test.com",
            "password": "Test@1234",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r["Content-Type"], "application/json")

    # ---- Register AJAX ----

    def test_register_ajax_success(self):
        r = self.client.post(reverse("register"), {
            "username": "newuser",
            "email": "new@test.com",
            "password": "Test@1234",
            "confirmation": "Test@1234",
            "role": "attendee",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertIn("redirect", data)
        self.assertTrue(User.objects.filter(username="newuser").exists())

    def test_register_ajax_duplicate_username(self):
        r = self.client.post(reverse("register"), {
            "username": "testuser",
            "email": "dup@test.com",
            "password": "Test@1234",
            "confirmation": "Test@1234",
            "role": "attendee",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("error", data)
        self.assertIn("taken", data["error"].lower())

    def test_register_ajax_password_mismatch(self):
        r = self.client.post(reverse("register"), {
            "username": "mismatch",
            "email": "m@test.com",
            "password": "Test@1234",
            "confirmation": "Diff@1234",
            "role": "attendee",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("error", data)

    def test_register_ajax_invalid_email(self):
        r = self.client.post(reverse("register"), {
            "username": "bademail",
            "email": "notanemail",
            "password": "Test@1234",
            "confirmation": "Test@1234",
            "role": "attendee",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("error", data)

    def test_register_ajax_invalid_role(self):
        r = self.client.post(reverse("register"), {
            "username": "badrole",
            "email": "bad@test.com",
            "password": "Test@1234",
            "confirmation": "Test@1234",
            "role": "admin",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("error", data)

    def test_register_ajax_short_username(self):
        r = self.client.post(reverse("register"), {
            "username": "ab",
            "email": "s@test.com",
            "password": "Test@1234",
            "confirmation": "Test@1234",
            "role": "attendee",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("error", data)

    def test_register_ajax_short_password(self):
        r = self.client.post(reverse("register"), {
            "username": "shortpw",
            "email": "sp@test.com",
            "password": "12345",
            "confirmation": "12345",
            "role": "attendee",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("error", data)

    def test_register_ajax_empty_fields(self):
        r = self.client.post(reverse("register"), {
            "username": "",
            "email": "",
            "password": "",
            "confirmation": "",
            "role": "",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r.status_code, 400)
        data = r.json()
        self.assertIn("error", data)

    def test_register_non_ajax_still_renders_html(self):
        r = self.client.post(reverse("register"), {
            "username": "testuser",
            "email": "dup@test.com",
            "password": "Test@1234",
            "confirmation": "Test@1234",
            "role": "attendee",
        })
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "text/html; charset=utf-8")

    def test_register_ajax_returns_json_content_type(self):
        r = self.client.post(reverse("register"), {
            "username": "jsonuser",
            "email": "json@test.com",
            "password": "Test@1234",
            "confirmation": "Test@1234",
            "role": "attendee",
        }, **self.AJAX_HEADERS)
        self.assertEqual(r["Content-Type"], "application/json")


class SoftDeleteModelTests(TestCase):
    """Tests for SoftDeleteModel behaviour across all models."""

    def setUp(self):
        self.organizer = User.objects.create_user("organizer", "org@test.com", "Test@1234")
        self.attendee = User.objects.create_user("attendee", "att@test.com", "Test@1234")
        self.category = Category.objects.create(name="Music")
        self.event = Event.objects.create(
            title="Concert",
            description="A great concert",
            category=self.category,
            organizer=self.organizer,
            location="Lisbon",
            date=date.today() + timedelta(days=7),
            time=time(20, 0),
            capacity=10,
        )

    # ── Basic soft delete lifecycle ──────────────────────────────────

    def test_soft_delete_sets_deleted_at(self):
        self.event.delete()
        self.event.refresh_from_db()
        self.assertIsNotNone(self.event.deleted_at)

    def test_soft_deleted_excluded_from_default_manager(self):
        self.event.delete()
        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())

    def test_soft_deleted_visible_in_all_objects(self):
        self.event.delete()
        self.assertTrue(Event.all_objects.filter(pk=self.event.pk).exists())

    def test_restore_clears_deleted_at(self):
        self.event.delete()
        self.event.restore()
        self.event.refresh_from_db()
        self.assertIsNone(self.event.deleted_at)
        self.assertTrue(Event.objects.filter(pk=self.event.pk).exists())

    def test_hard_delete_removes_from_database(self):
        pk = self.event.pk
        self.event.hard_delete()
        self.assertFalse(Event.all_objects.filter(pk=pk).exists())

    def test_queryset_delete_soft_deletes_bulk(self):
        Event.objects.filter(pk=self.event.pk).delete()
        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())
        self.assertTrue(Event.all_objects.filter(pk=self.event.pk).exists())

    # ── Category soft delete ─────────────────────────────────────────

    def test_category_soft_delete(self):
        self.category.delete()
        self.assertFalse(Category.objects.filter(pk=self.category.pk).exists())
        self.assertTrue(Category.all_objects.filter(pk=self.category.pk).exists())

    def test_category_restore(self):
        self.category.delete()
        self.category.restore()
        self.assertTrue(Category.objects.filter(pk=self.category.pk).exists())

    # ── UserProfile soft delete ──────────────────────────────────────

    def test_userprofile_soft_delete(self):
        profile = UserProfile.objects.create(user=self.organizer)
        profile.delete()
        self.assertFalse(UserProfile.objects.filter(user=self.organizer).exists())
        self.assertTrue(UserProfile.all_objects.filter(user=self.organizer).exists())

    # ── Reservation soft delete & re-reserve ─────────────────────────

    def test_reservation_soft_delete(self):
        reservation, _ = self.event.reserve(self.attendee)
        reservation.delete()
        self.assertFalse(Reservation.objects.filter(pk=reservation.pk).exists())
        self.assertTrue(Reservation.all_objects.filter(pk=reservation.pk).exists())

    def test_reserve_restores_soft_deleted_reservation(self):
        reservation, _ = self.event.reserve(self.attendee)
        reservation.delete()
        new_reservation, error = self.event.reserve(self.attendee)
        self.assertIsNone(error)
        self.assertIsNotNone(new_reservation)
        self.assertEqual(new_reservation.pk, reservation.pk)
        self.assertIsNone(new_reservation.deleted_at)

    # ── Favorite soft delete & toggle cycle ──────────────────────────

    def test_favorite_soft_delete(self):
        self.event.toggle_favorite(self.attendee)
        fav = Favorite.objects.get(user=self.attendee, event=self.event)
        fav.delete()
        self.assertFalse(Favorite.objects.filter(pk=fav.pk).exists())
        self.assertTrue(Favorite.all_objects.filter(pk=fav.pk).exists())

    def test_toggle_favorite_restores_soft_deleted(self):
        self.event.toggle_favorite(self.attendee)  # add
        self.event.toggle_favorite(self.attendee)  # remove (soft delete)
        result = self.event.toggle_favorite(self.attendee)  # restore
        self.assertTrue(result)
        self.assertTrue(Favorite.objects.filter(user=self.attendee, event=self.event).exists())

    # ── Review soft delete & re-review ───────────────────────────────

    def test_review_soft_delete(self):
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        review, _ = self.event.add_review(self.attendee, 5, "Great!")
        review.delete()
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())
        self.assertTrue(Review.all_objects.filter(pk=review.pk).exists())

    def test_add_review_restores_soft_deleted(self):
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        review, _ = self.event.add_review(self.attendee, 5, "Great!")
        review.delete()
        new_review, error = self.event.add_review(self.attendee, 3, "Okay")
        self.assertIsNone(error)
        self.assertIsNotNone(new_review)
        self.assertEqual(new_review.pk, review.pk)
        self.assertEqual(new_review.rating, 3)

    # ── Notification soft delete ─────────────────────────────────────

    def test_notification_soft_delete(self):
        notif = Notification.objects.create(
            recipient=self.attendee,
            notification_type="reservation",
            title="Test",
            message="msg",
        )
        notif.delete()
        self.assertFalse(Notification.objects.filter(pk=notif.pk).exists())
        self.assertTrue(Notification.all_objects.filter(pk=notif.pk).exists())

    # ── UniqueConstraint allows re-creation after soft delete ────────

    def test_unique_reservation_after_soft_delete(self):
        reservation, _ = self.event.reserve(self.attendee)
        reservation.delete()
        new_res, error = self.event.reserve(self.attendee)
        self.assertIsNone(error)

    def test_unique_review_after_soft_delete(self):
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        review, _ = self.event.add_review(self.attendee, 5, "Great!")
        review.delete()
        new_review, error = self.event.add_review(self.attendee, 4, "Good")
        self.assertIsNone(error)

    def test_unique_favorite_after_soft_delete(self):
        self.event.toggle_favorite(self.attendee)  # add
        self.event.toggle_favorite(self.attendee)  # soft delete
        result = self.event.toggle_favorite(self.attendee)  # restore
        self.assertTrue(result)
