from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils import timezone

from .models import User, Category, Event, Reservation, Review, Favorite, Notification


class SoftDeleteAdmin(admin.ModelAdmin):
    """Base admin that shows soft-deleted records and provides restore."""

    def get_queryset(self, request):
        return self.model.all_objects.all()

    def is_deleted(self, obj):
        return obj.deleted_at is not None
    is_deleted.boolean = True
    is_deleted.short_description = "Deleted?"

    @admin.action(description="Restore selected items")
    def restore_selected(self, request, queryset):
        queryset.update(deleted_at=None)


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        ("Extra", {"fields": ("bio", "avatar", "phone")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Extra", {"fields": ("bio", "avatar", "phone")}),
    )


@admin.register(Category)
class CategoryAdmin(SoftDeleteAdmin):
    list_display = ("name", "slug", "is_deleted")
    list_filter = ("deleted_at",)
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}
    actions = ["restore_selected"]


class ReservationInline(admin.TabularInline):
    model = Reservation
    extra = 0
    readonly_fields = ("user", "status", "created_at")
    can_delete = False


@admin.register(Event)
class EventAdmin(SoftDeleteAdmin):
    list_display = ("title", "organizer", "category", "start_date", "start_time", "capacity", "price", "status", "is_deleted")
    list_filter = ("status", "category", "start_date", "deleted_at")
    search_fields = ("title", "description", "organizer__username")
    readonly_fields = ("slug", "created_at", "updated_at")
    autocomplete_fields = ("organizer", "category")
    inlines = [ReservationInline]
    actions = ["publish_events", "cancel_events", "restore_selected"]

    @admin.action(description="Publish selected events")
    def publish_events(self, request, queryset):
        queryset.update(status=Event.PUBLISHED, published_at=timezone.now())

    @admin.action(description="Cancel selected events")
    def cancel_events(self, request, queryset):
        queryset.update(status=Event.CANCELLED)


@admin.register(Reservation)
class ReservationAdmin(SoftDeleteAdmin):
    list_display = ("user", "event", "status", "created_at", "is_deleted")
    list_filter = ("status", "deleted_at")
    search_fields = ("user__username", "event__title")
    readonly_fields = ("created_at",)
    actions = ["cancel_reservations", "restore_selected"]

    @admin.action(description="Cancel selected reservations")
    def cancel_reservations(self, request, queryset):
        queryset.filter(status="confirmed").update(status="cancelled")


@admin.register(Review)
class ReviewAdmin(SoftDeleteAdmin):
    list_display = ("user", "event", "rating", "created_at", "is_deleted")
    list_filter = ("rating", "deleted_at")
    search_fields = ("user__username", "event__title")
    readonly_fields = ("created_at",)
    actions = ["restore_selected"]


@admin.register(Favorite)
class FavoriteAdmin(SoftDeleteAdmin):
    list_display = ("user", "event", "created_at", "is_deleted")
    list_filter = ("deleted_at",)
    search_fields = ("user__username", "event__title")
    readonly_fields = ("created_at",)
    actions = ["restore_selected"]


@admin.register(Notification)
class NotificationAdmin(SoftDeleteAdmin):
    list_display = ("recipient", "notification_type", "title", "is_read", "created_at", "is_deleted")
    list_filter = ("notification_type", "deleted_at")
    search_fields = ("recipient__username", "title")
    readonly_fields = ("created_at", "read_at")
    actions = ["mark_as_read", "restore_selected"]

    @admin.action(description="Mark selected as read")
    def mark_as_read(self, request, queryset):
        queryset.filter(read_at__isnull=True).update(read_at=timezone.now())
