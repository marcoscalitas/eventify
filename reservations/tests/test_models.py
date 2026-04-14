from datetime import date, time, timedelta

from django.contrib.auth.models import User
from django.test import TestCase

from ..models import Category, Event, Favorite, Reservation, Review
from ..services.booking import reserve
from ..services.review import add_review
from ..services.favorite import toggle_favorite


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
        reservation, error = reserve(self.attendee, self.event)
        self.assertIsNotNone(reservation)
        self.assertIsNone(error)
        self.assertEqual(reservation.status, "confirmed")
        self.assertEqual(self.event.spots_left(), 1)

    def test_reserve_duplicate(self):
        reserve(self.attendee, self.event)
        _, error = reserve(self.attendee, self.event)
        self.assertEqual(error, "Already reserved.")

    def test_reserve_full(self):
        user2 = User.objects.create_user("user2", "u2@test.com", "Test@1234")
        reserve(self.attendee, self.event)
        reserve(user2, self.event)
        user3 = User.objects.create_user("user3", "u3@test.com", "Test@1234")
        _, error = reserve(user3, self.event)
        self.assertEqual(error, "No spots available.")

    def test_add_review_success(self):
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        review, error = add_review(self.attendee, self.event, 5, "Great!")
        self.assertIsNotNone(review)
        self.assertIsNone(error)
        self.assertEqual(review.rating, 5)

    def test_add_review_no_reservation(self):
        _, error = add_review(self.attendee, self.event, 5, "Great!")
        self.assertEqual(error, "You must have a reservation to review.")

    def test_add_review_duplicate(self):
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        add_review(self.attendee, self.event, 5, "Great!")
        _, error = add_review(self.attendee, self.event, 4, "Again")
        self.assertEqual(error, "You already reviewed this event.")

    def test_toggle_favorite(self):
        result = toggle_favorite(self.attendee, self.event)
        self.assertTrue(result)
        self.assertTrue(Favorite.objects.filter(user=self.attendee, event=self.event).exists())

        result = toggle_favorite(self.attendee, self.event)
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
        reservation, _ = reserve(self.attendee, self.event)
        reservation.cancel()
        reservation.refresh_from_db()
        self.assertEqual(reservation.status, "cancelled")
