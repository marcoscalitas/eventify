"""Tests to achieve 100% code coverage across all application files."""
from datetime import date, time, timedelta
from io import BytesIO
from unittest.mock import patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from rolepermissions.roles import assign_role

from ..admin import (
    EventAdmin, ReservationAdmin, NotificationAdmin,
)
from ..forms.validators import validate_file_size
from ..models import (
    Category, Event, Favorite, Notification, Reservation, Review,
)
from ..serializers import EventSerializer
from ..services.booking import cancel_reservation, reserve

User = get_user_model()


class ValidateFileSizeTests(TestCase):
    def test_file_under_limit_passes(self):
        f = SimpleUploadedFile("ok.jpg", b"x" * 100)
        validate_file_size(f)  # should not raise

    def test_file_over_limit_raises(self):
        from django import forms
        f = SimpleUploadedFile("big.jpg", b"x" * (6 * 1024 * 1024))
        with self.assertRaises(forms.ValidationError):
            validate_file_size(f)


class CancelReservationServiceTests(TestCase):
    def setUp(self):
        self.org = User.objects.create_user("org", "o@t.com", "Test@1234")
        self.att = User.objects.create_user("att", "a@t.com", "Test@1234")
        self.event = Event.objects.create(
            title="E", description="D", organizer=self.org,
            venue="L", start_date=date.today() + timedelta(days=7),
            start_time=time(20, 0), capacity=10,
        )

    def test_cancel_reservation_standalone(self):
        reservation, _ = reserve(self.att, self.event)
        cancel_reservation(reservation)
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, Reservation.CANCELLED)

    def test_reserve_integrity_error_race_condition(self):
        with patch("reservations.services.booking.Reservation.objects.create", side_effect=IntegrityError):
            result, error = reserve(self.att, self.event)
        self.assertIsNone(result)
        self.assertEqual(error, "Already reserved.")


class ModelStrTests(TestCase):
    def setUp(self):
        self.org = User.objects.create_user("org", "o@t.com", "Test@1234")
        self.att = User.objects.create_user("att", "a@t.com", "Test@1234")
        self.cat = Category.objects.create(name="Music")
        self.event = Event.objects.create(
            title="Concert", description="D", category=self.cat,
            organizer=self.org, venue="L",
            start_date=date.today() + timedelta(days=7),
            start_time=time(20, 0), capacity=10,
        )

    def test_event_str(self):
        self.assertIn("Concert", str(self.event))

    def test_reservation_str(self):
        res, _ = reserve(self.att, self.event)
        self.assertIn("att", str(res))
        self.assertIn("confirmed", str(res))

    def test_review_str(self):
        Reservation.objects.create(user=self.att, event=self.event, status="confirmed")
        review = Review.objects.create(user=self.att, event=self.event, rating=5)
        self.assertIn("5★", str(review))

    def test_favorite_str(self):
        fav = Favorite.objects.create(user=self.att, event=self.event)
        self.assertIn("♥", str(fav))

    def test_notification_str(self):
        n = Notification.objects.create(
            recipient=self.att, notification_type="reservation_confirmed",
            title="Test", message="msg",
        )
        self.assertIn("Test", str(n))

    def test_userprofile_str(self):
        self.assertEqual(str(self.att), "att")


class SoftDeleteQuerySetExtraTests(TestCase):
    def setUp(self):
        self.org = User.objects.create_user("org", "o@t.com", "Test@1234")
        self.cat = Category.objects.create(name="Music")

    def test_dead_returns_soft_deleted(self):
        self.cat.delete()
        dead = Category.all_objects.get_queryset().dead()
        self.assertTrue(dead.filter(pk=self.cat.pk).exists())

    def test_hard_delete_queryset(self):
        pk = self.cat.pk
        Category.all_objects.filter(pk=pk).hard_delete()
        self.assertFalse(Category.all_objects.filter(pk=pk).exists())


class AdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.site = AdminSite()
        self.admin_user = User.objects.create_superuser("admin", "a@t.com", "Test@1234")
        self.org = User.objects.create_user("org", "o@t.com", "Test@1234")
        self.cat = Category.objects.create(name="Music")
        self.event = Event.objects.create(
            title="E", description="D", category=self.cat,
            organizer=self.org, venue="L",
            start_date=date.today() + timedelta(days=7),
            start_time=time(20, 0), capacity=10,
        )

    def test_get_queryset_includes_soft_deleted(self):
        admin = EventAdmin(Event, self.site)
        self.event.delete()
        request = self.factory.get("/admin/")
        request.user = self.admin_user
        qs = admin.get_queryset(request)
        self.assertIn(self.event, qs)

    def test_is_deleted_flag(self):
        admin = EventAdmin(Event, self.site)
        self.assertFalse(admin.is_deleted(self.event))
        self.event.delete()
        self.event.refresh_from_db()
        self.assertTrue(admin.is_deleted(self.event))

    def test_restore_selected(self):
        admin = EventAdmin(Event, self.site)
        self.event.delete()
        request = self.factory.post("/admin/")
        request.user = self.admin_user
        admin.restore_selected(request, Event.all_objects.filter(pk=self.event.pk))
        self.event.refresh_from_db()
        self.assertIsNone(self.event.deleted_at)

    def test_cancel_events(self):
        admin = EventAdmin(Event, self.site)
        request = self.factory.post("/admin/")
        request.user = self.admin_user
        admin.cancel_events(request, Event.objects.filter(pk=self.event.pk))
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.CANCELLED)

    def test_publish_events(self):
        admin = EventAdmin(Event, self.site)
        self.event.status = Event.CANCELLED
        self.event.save()
        request = self.factory.post("/admin/")
        request.user = self.admin_user
        admin.publish_events(request, Event.all_objects.filter(pk=self.event.pk))
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, Event.PUBLISHED)

    def test_cancel_reservations_action(self):
        att = User.objects.create_user("att", "a2@t.com", "Test@1234")
        res, _ = reserve(att, self.event)
        admin = ReservationAdmin(Reservation, self.site)
        request = self.factory.post("/admin/")
        request.user = self.admin_user
        admin.cancel_reservations(request, Reservation.objects.filter(pk=res.pk))
        res.refresh_from_db()
        self.assertEqual(res.status, "cancelled")

    def test_mark_as_read_action(self):
        att = User.objects.create_user("att", "a2@t.com", "Test@1234")
        n = Notification.objects.create(
            recipient=att, notification_type="reservation_confirmed",
            title="T", message="m",
        )
        admin = NotificationAdmin(Notification, self.site)
        request = self.factory.post("/admin/")
        request.user = self.admin_user
        admin.mark_as_read(request, Notification.objects.filter(pk=n.pk))
        n.refresh_from_db()
        self.assertTrue(n.is_read)


class EventSerializerImageTests(TestCase):
    def setUp(self):
        self.org = User.objects.create_user("org", "o@t.com", "Test@1234")
        self.event = Event.objects.create(
            title="E", description="D" * 200, organizer=self.org,
            venue="L", start_date=date.today() + timedelta(days=7),
            start_time=time(20, 0), capacity=10,
        )

    def test_no_image_returns_empty_string(self):
        serializer = EventSerializer(self.event, context={"truncate": False})
        self.assertEqual(serializer.data["image"], "")

    def test_image_without_request(self):
        self.event.image = "events/test.jpg"
        self.event.save()
        serializer = EventSerializer(self.event, context={"truncate": False})
        self.assertIn("events/test.jpg", serializer.data["image"])

    def test_image_with_request(self):
        self.event.image = "events/test.jpg"
        self.event.save()
        factory = RequestFactory()
        request = factory.get("/")
        serializer = EventSerializer(self.event, context={"truncate": True, "request": request})
        self.assertIn("http", serializer.data["image"])
        self.assertEqual(len(serializer.data["description"]), 150)


@override_settings(RATELIMIT_ENABLE=False)
class DecoratorAjax403Tests(TestCase):
    def setUp(self):
        self.att = User.objects.create_user("att", "a@t.com", "Test@1234")
        assign_role(self.att, "attendee")

    def test_role_required_ajax_returns_json_403(self):
        self.client.login(username="att", password="Test@1234")
        response = self.client.get(
            reverse("create_event"),
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertIn("error", data)

    def test_role_required_unauthenticated_redirects(self):
        response = self.client.get(reverse("create_event"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)


class LoginFormCleanPasswordTests(TestCase):
    def test_login_form_strong_password_valid(self):
        from ..forms import LoginForm
        form = LoginForm(data={"email": "u@t.com", "password": "Test@1234"})
        self.assertTrue(form.is_valid())

    def test_login_form_weak_password_invalid(self):
        from ..forms import LoginForm
        form = LoginForm(data={"email": "u@t.com", "password": "weakpass1234"})
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)


class RegisterFormCleanPasswordTests(TestCase):
    def test_register_form_strong_password_valid(self):
        from ..forms import RegisterForm
        form = RegisterForm(data={
            "username": "testuser", "email": "t@t.com",
            "password": "Test@1234", "confirmation": "Test@1234",
            "role": "attendee",
        })
        self.assertTrue(form.is_valid())

    def test_register_form_weak_password_invalid(self):
        from ..forms import RegisterForm
        form = RegisterForm(data={
            "username": "testuser2", "email": "t2@t.com",
            "password": "weakpass1234", "confirmation": "weakpass1234",
            "role": "attendee",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("password", form.errors)


class RateLimitedErrorTests(TestCase):
    def test_ratelimited_error_returns_429(self):
        from ..views.api import ratelimited_error
        factory = RequestFactory()
        request = factory.get("/")
        response = ratelimited_error(request, Exception())
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.data["error"], "Too many requests. Please slow down.")


@override_settings(RATELIMIT_ENABLE=False)
class EditEventInvalidFormTests(TestCase):
    def setUp(self):
        self.org = User.objects.create_user("org", "o@t.com", "Test@1234")
        assign_role(self.org, "organizer")
        self.event = Event.objects.create(
            title="E", description="D", organizer=self.org,
            venue="L", start_date=date.today() + timedelta(days=7),
            start_time=time(20, 0), capacity=10,
        )

    def test_edit_event_get_renders_form(self):
        self.client.login(username="org", password="Test@1234")
        r = self.client.get(reverse("edit_event", args=[self.event.id]))
        self.assertEqual(r.status_code, 200)

    def test_edit_event_invalid_form_rerenders(self):
        self.client.login(username="org", password="Test@1234")
        r = self.client.post(reverse("edit_event", args=[self.event.id]), {
            "title": "", "description": "", "venue": "",
            "start_date": "", "start_time": "", "capacity": 0, "price": "0",
        })
        self.assertEqual(r.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.title, "E")


@override_settings(RATELIMIT_ENABLE=False)
class NotifyEventUpdatedTests(TestCase):
    def test_notify_event_updated_with_attendees(self):
        org = User.objects.create_user("org", "o@t.com", "Test@1234")
        assign_role(org, "organizer")
        att = User.objects.create_user("att", "a@t.com", "Test@1234")
        assign_role(att, "attendee")
        event = Event.objects.create(
            title="E", description="D", organizer=org,
            venue="L", start_date=date.today() + timedelta(days=7),
            start_time=time(20, 0), capacity=10,
        )
        reserve(att, event)
        Notification.objects.all().delete()

        self.client.login(username="org", password="Test@1234")
        self.client.post(reverse("edit_event", args=[event.id]), {
            "title": "Updated", "description": "New desc",
            "venue": "L", "start_date": (date.today() + timedelta(days=7)).isoformat(),
            "start_time": "20:00", "capacity": 10, "price": "0",
        })
        self.assertTrue(
            Notification.objects.filter(
                recipient=att, notification_type="event_updated"
            ).exists()
        )


@override_settings(RATELIMIT_ENABLE=False)
class RegisterIntegrityErrorTests(TestCase):
    def test_register_integrity_error_ajax(self):
        with patch("reservations.views.auth.User.objects.create_user", side_effect=IntegrityError):
            r = self.client.post(reverse("register"), {
                "username": "newunique",
                "email": "new@t.com",
                "password": "Test@1234",
                "confirmation": "Test@1234",
                "role": "attendee",
            }, HTTP_ACCEPT="application/json")
            self.assertEqual(r.status_code, 400)
            self.assertIn("taken", r.json()["error"].lower())


class ProfileAvatarUploadTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("att", "a@t.com", "Test@1234")

    def _make_image(self):
        from PIL import Image
        img = Image.new("RGB", (10, 10), color="red")
        buf = BytesIO()
        img.save(buf, format="JPEG")
        buf.seek(0)
        return SimpleUploadedFile("avatar.jpg", buf.read(), content_type="image/jpeg")

    def test_profile_upload_avatar(self):
        self.client.login(username="att", password="Test@1234")
        r = self.client.post(reverse("profile"), {
            "first_name": "A",
            "last_name": "B",
            "email": "a@t.com",
            "bio": "hi",
            "avatar": self._make_image(),
        })
        self.assertEqual(r.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.avatar)
