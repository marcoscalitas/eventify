from datetime import date, time, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase

from ..models import (
    Category, Event, Favorite, Notification, Reservation, Review,
)
from ..services.booking import reserve
from ..services.review import add_review
from ..services.favorite import toggle_favorite

User = get_user_model()


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
            venue="Lisbon",
            start_date=date.today() + timedelta(days=7),
            start_time=time(20, 0),
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

    def test_category_hard_delete(self):
        pk = self.category.pk
        self.category.hard_delete()
        self.assertFalse(Category.all_objects.filter(pk=pk).exists())

    # ── Reservation soft delete & re-reserve ─────────────────────────

    def test_reservation_soft_delete(self):
        reservation, _ = reserve(self.attendee, self.event)
        reservation.delete()
        self.assertFalse(Reservation.objects.filter(pk=reservation.pk).exists())
        self.assertTrue(Reservation.all_objects.filter(pk=reservation.pk).exists())

    def test_reservation_hard_delete(self):
        reservation, _ = reserve(self.attendee, self.event)
        pk = reservation.pk
        reservation.hard_delete()
        self.assertFalse(Reservation.all_objects.filter(pk=pk).exists())

    def test_reserve_restores_soft_deleted_reservation(self):
        reservation, _ = reserve(self.attendee, self.event)
        reservation.delete()
        new_reservation, error = reserve(self.attendee, self.event)
        self.assertIsNone(error)
        self.assertIsNotNone(new_reservation)
        self.assertEqual(new_reservation.pk, reservation.pk)
        self.assertIsNone(new_reservation.deleted_at)

    # ── Favorite soft delete & toggle cycle ──────────────────────────

    def test_favorite_soft_delete(self):
        toggle_favorite(self.attendee, self.event)
        fav = Favorite.objects.get(user=self.attendee, event=self.event)
        fav.delete()
        self.assertFalse(Favorite.objects.filter(pk=fav.pk).exists())
        self.assertTrue(Favorite.all_objects.filter(pk=fav.pk).exists())

    def test_favorite_hard_delete(self):
        toggle_favorite(self.attendee, self.event)
        fav = Favorite.objects.get(user=self.attendee, event=self.event)
        pk = fav.pk
        fav.hard_delete()
        self.assertFalse(Favorite.all_objects.filter(pk=pk).exists())

    def test_toggle_favorite_restores_soft_deleted(self):
        toggle_favorite(self.attendee, self.event)  # add
        toggle_favorite(self.attendee, self.event)  # remove (soft delete)
        result = toggle_favorite(self.attendee, self.event)  # restore
        self.assertTrue(result)
        self.assertTrue(Favorite.objects.filter(user=self.attendee, event=self.event).exists())

    # ── Review soft delete & re-review ───────────────────────────────

    def test_review_soft_delete(self):
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        review, _ = add_review(self.attendee, self.event, 5, "Great!")
        review.delete()
        self.assertFalse(Review.objects.filter(pk=review.pk).exists())
        self.assertTrue(Review.all_objects.filter(pk=review.pk).exists())

    def test_review_hard_delete(self):
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        review, _ = add_review(self.attendee, self.event, 5, "Great!")
        pk = review.pk
        review.hard_delete()
        self.assertFalse(Review.all_objects.filter(pk=pk).exists())

    def test_add_review_restores_soft_deleted(self):
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        review, _ = add_review(self.attendee, self.event, 5, "Great!")
        review.delete()
        new_review, error = add_review(self.attendee, self.event, 3, "Okay")
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

    def test_notification_restore(self):
        notif = Notification.objects.create(
            recipient=self.attendee,
            notification_type="reservation",
            title="Test",
            message="msg",
        )
        notif.delete()
        notif.restore()
        self.assertTrue(Notification.objects.filter(pk=notif.pk).exists())

    def test_notification_hard_delete(self):
        notif = Notification.objects.create(
            recipient=self.attendee,
            notification_type="reservation",
            title="Test",
            message="msg",
        )
        pk = notif.pk
        notif.hard_delete()
        self.assertFalse(Notification.all_objects.filter(pk=pk).exists())

    # ── UniqueConstraint allows re-creation after soft delete ────────

    def test_unique_reservation_after_soft_delete(self):
        reservation, _ = reserve(self.attendee, self.event)
        reservation.delete()
        new_res, error = reserve(self.attendee, self.event)
        self.assertIsNone(error)

    def test_unique_review_after_soft_delete(self):
        Reservation.objects.create(user=self.attendee, event=self.event, status="confirmed")
        review, _ = add_review(self.attendee, self.event, 5, "Great!")
        review.delete()
        new_review, error = add_review(self.attendee, self.event, 4, "Good")
        self.assertIsNone(error)

    def test_unique_favorite_after_soft_delete(self):
        toggle_favorite(self.attendee, self.event)  # add
        toggle_favorite(self.attendee, self.event)  # soft delete
        result = toggle_favorite(self.attendee, self.event)  # restore
        self.assertTrue(result)
