from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import UserProfile


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


@override_settings(RATELIMIT_ENABLE=False)
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
