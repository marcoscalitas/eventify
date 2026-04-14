import json
from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from rolepermissions.roles import assign_role

from ..models import Category, Event, Notification, Reservation, UserProfile
from ..services.booking import reserve


@override_settings(RATELIMIT_ENABLE=False)
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
        reservation, err = reserve(att, event)
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
