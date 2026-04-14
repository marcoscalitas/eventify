from datetime import date, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from ..models import Category


class FormTests(TestCase):
    def test_register_form_passwords_mismatch(self):
        from ..forms import RegisterForm
        form = RegisterForm(data={
            "username": "newuser",
            "email": "new@test.com",
            "password": "Test@1234",
            "confirmation": "Diff@1234",
            "role": "attendee",
        })
        self.assertFalse(form.is_valid())

    def test_register_form_valid(self):
        from ..forms import RegisterForm
        form = RegisterForm(data={
            "username": "newuser",
            "email": "new@test.com",
            "password": "Test@1234",
            "confirmation": "Test@1234",
            "role": "attendee",
        })
        self.assertTrue(form.is_valid())

    def test_event_form_invalid_capacity(self):
        from ..forms import EventForm
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
        from ..forms import ReviewForm
        form = ReviewForm(data={"rating": 5, "comment": "Great!"})
        self.assertTrue(form.is_valid())


class BruteFormValidationTests(TestCase):
    """Brute-force validation tests for every form field boundary."""

    # ── LoginForm ────────────────────────────────────────────

    def test_login_empty_email(self):
        from ..forms import LoginForm
        form = LoginForm(data={"email": "", "password": "Test@1234"})
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_login_empty_password(self):
        from ..forms import LoginForm
        form = LoginForm(data={"email": "user@test.com", "password": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    def test_login_both_empty(self):
        from ..forms import LoginForm
        form = LoginForm(data={"email": "", "password": ""})
        self.assertFalse(form.is_valid())

    def test_login_missing_fields(self):
        from ..forms import LoginForm
        form = LoginForm(data={})
        self.assertFalse(form.is_valid())

    def test_login_invalid_email(self):
        from ..forms import LoginForm
        form = LoginForm(data={"email": "not-an-email", "password": "Test@1234"})
        self.assertFalse(form.is_valid())

    def test_login_valid(self):
        from ..forms import LoginForm
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
        from ..forms import RegisterForm
        form = RegisterForm(data=self._register_data(username="ab"))
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_register_username_exactly_3(self):
        from ..forms import RegisterForm
        form = RegisterForm(data=self._register_data(username="abc"))
        self.assertTrue(form.is_valid())

    def test_register_username_too_long(self):
        from ..forms import RegisterForm
        form = RegisterForm(data=self._register_data(username="a" * 151))
        self.assertFalse(form.is_valid())

    def test_register_username_exactly_150(self):
        from ..forms import RegisterForm
        form = RegisterForm(data=self._register_data(username="a" * 150))
        self.assertTrue(form.is_valid())

    def test_register_username_taken(self):
        from ..forms import RegisterForm
        User.objects.create_user("taken", "t@t.com", "Test@1234")
        form = RegisterForm(data=self._register_data(username="taken"))
        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)

    def test_register_empty_email(self):
        from ..forms import RegisterForm
        form = RegisterForm(data=self._register_data(email=""))
        self.assertFalse(form.is_valid())

    def test_register_invalid_email(self):
        from ..forms import RegisterForm
        form = RegisterForm(data=self._register_data(email="not-an-email"))
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_register_password_too_short(self):
        from ..forms import RegisterForm
        form = RegisterForm(data=self._register_data(
            password="12345", confirmation="12345"
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)

    def test_register_password_exactly_8(self):
        from ..forms import RegisterForm
        form = RegisterForm(data=self._register_data(
            password="Test@123", confirmation="Test@123"
        ))
        self.assertTrue(form.is_valid())

    def test_register_passwords_mismatch(self):
        from ..forms import RegisterForm
        form = RegisterForm(data=self._register_data(confirmation="Wrong@1234"))
        self.assertFalse(form.is_valid())

    def test_register_invalid_role(self):
        from ..forms import RegisterForm
        form = RegisterForm(data=self._register_data(role="admin"))
        self.assertFalse(form.is_valid())
        self.assertIn("role", form.errors)

    def test_register_empty_role(self):
        from ..forms import RegisterForm
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
        from ..forms import EventForm
        form = EventForm(data=self._event_data())
        self.assertTrue(form.is_valid())

    def test_event_empty_title(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(title=""))
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)

    def test_event_title_max_length(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(title="a" * 201))
        self.assertFalse(form.is_valid())

    def test_event_title_exactly_200(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(title="a" * 200))
        self.assertTrue(form.is_valid())

    def test_event_empty_description(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(description=""))
        self.assertFalse(form.is_valid())

    def test_event_empty_location(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(location=""))
        self.assertFalse(form.is_valid())

    def test_event_location_max_length(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(location="x" * 256))
        self.assertFalse(form.is_valid())

    def test_event_date_in_past(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(
            date=(date.today() - timedelta(days=1)).isoformat()
        ))
        self.assertFalse(form.is_valid())
        self.assertIn("date", form.errors)

    def test_event_date_today(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(date=date.today().isoformat()))
        self.assertTrue(form.is_valid())

    def test_event_date_far_past(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(date="2020-01-01"))
        self.assertFalse(form.is_valid())

    def test_event_empty_date(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(date=""))
        self.assertFalse(form.is_valid())

    def test_event_invalid_date_format(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(date="not-a-date"))
        self.assertFalse(form.is_valid())

    def test_event_empty_time(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(time=""))
        self.assertFalse(form.is_valid())

    def test_event_capacity_zero(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(capacity=0))
        self.assertFalse(form.is_valid())
        self.assertIn("capacity", form.errors)

    def test_event_capacity_negative(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(capacity=-5))
        self.assertFalse(form.is_valid())

    def test_event_capacity_one(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data(capacity=1))
        self.assertTrue(form.is_valid())

    def test_event_no_category_ok(self):
        from ..forms import EventForm
        data = self._event_data()
        data.pop("category")
        form = EventForm(data=data)
        self.assertTrue(form.is_valid())

    def test_event_no_image_ok(self):
        from ..forms import EventForm
        form = EventForm(data=self._event_data())
        self.assertTrue(form.is_valid())

    # ── ProfileForm ──────────────────────────────────────────

    def test_profile_all_empty_is_valid(self):
        from ..forms import ProfileForm
        form = ProfileForm(data={
            "first_name": "", "last_name": "", "email": "", "bio": "",
        })
        self.assertTrue(form.is_valid())

    def test_profile_invalid_email(self):
        from ..forms import ProfileForm
        form = ProfileForm(data={
            "first_name": "", "last_name": "", "email": "bad", "bio": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)

    def test_profile_first_name_too_long(self):
        from ..forms import ProfileForm
        form = ProfileForm(data={
            "first_name": "a" * 151, "last_name": "", "email": "", "bio": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("first_name", form.errors)

    def test_profile_last_name_too_long(self):
        from ..forms import ProfileForm
        form = ProfileForm(data={
            "first_name": "", "last_name": "a" * 151, "email": "", "bio": "",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("last_name", form.errors)

    def test_profile_bio_max_length(self):
        from ..forms import ProfileForm
        form = ProfileForm(data={
            "first_name": "", "last_name": "", "email": "",
            "bio": "x" * 501,
        })
        self.assertFalse(form.is_valid())
        self.assertIn("bio", form.errors)

    def test_profile_bio_exactly_500(self):
        from ..forms import ProfileForm
        form = ProfileForm(data={
            "first_name": "", "last_name": "", "email": "",
            "bio": "x" * 500,
        })
        self.assertTrue(form.is_valid())

    # ── ReviewForm ───────────────────────────────────────────

    def test_review_rating_zero(self):
        from ..forms import ReviewForm
        form = ReviewForm(data={"rating": 0, "comment": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)

    def test_review_rating_negative(self):
        from ..forms import ReviewForm
        form = ReviewForm(data={"rating": -1, "comment": ""})
        self.assertFalse(form.is_valid())

    def test_review_rating_six(self):
        from ..forms import ReviewForm
        form = ReviewForm(data={"rating": 6, "comment": ""})
        self.assertFalse(form.is_valid())
        self.assertIn("rating", form.errors)

    def test_review_rating_missing(self):
        from ..forms import ReviewForm
        form = ReviewForm(data={"comment": "hi"})
        self.assertFalse(form.is_valid())

    def test_review_rating_one(self):
        from ..forms import ReviewForm
        form = ReviewForm(data={"rating": 1, "comment": ""})
        self.assertTrue(form.is_valid())

    def test_review_rating_five(self):
        from ..forms import ReviewForm
        form = ReviewForm(data={"rating": 5, "comment": ""})
        self.assertTrue(form.is_valid())

    def test_review_comment_too_long(self):
        from ..forms import ReviewForm
        form = ReviewForm(data={"rating": 3, "comment": "x" * 1001})
        self.assertFalse(form.is_valid())
        self.assertIn("comment", form.errors)

    def test_review_comment_exactly_1000(self):
        from ..forms import ReviewForm
        form = ReviewForm(data={"rating": 3, "comment": "x" * 1000})
        self.assertTrue(form.is_valid())

    def test_review_empty_comment_ok(self):
        from ..forms import ReviewForm
        form = ReviewForm(data={"rating": 4})
        self.assertTrue(form.is_valid())
