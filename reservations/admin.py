from django.contrib import admin
from .models import UserProfile, Category, Event, Reservation, Review, Favorite, Notification


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "bio")
    search_fields = ("user__username",)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


class ReservationInline(admin.TabularInline):
    model = Reservation
    extra = 0
    readonly_fields = ("user", "status", "created_at")
    can_delete = False


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("title", "organizer", "category", "date", "time", "capacity", "is_active")
    list_filter = ("is_active", "category", "date")
    search_fields = ("title", "description", "organizer__username")
    readonly_fields = ("created_at", "updated_at")
    autocomplete_fields = ("organizer", "category")
    inlines = [ReservationInline]
    actions = ["deactivate_events", "activate_events"]

    @admin.action(description="Deactivate selected events")
    def deactivate_events(self, request, queryset):
        queryset.update(is_active=False)

    @admin.action(description="Activate selected events")
    def activate_events(self, request, queryset):
        queryset.update(is_active=True)


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("user__username", "event__title")
    readonly_fields = ("created_at",)
    actions = ["cancel_reservations"]

    @admin.action(description="Cancel selected reservations")
    def cancel_reservations(self, request, queryset):
        queryset.filter(status="confirmed").update(status="cancelled")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("user__username", "event__title")
    readonly_fields = ("created_at",)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "event", "created_at")
    search_fields = ("user__username", "event__title")
    readonly_fields = ("created_at",)


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("recipient", "notification_type", "title", "is_read", "created_at")
    list_filter = ("notification_type", "is_read")
    search_fields = ("title", "message", "recipient__username")
    readonly_fields = ("created_at",)
    actions = ["mark_as_read"]

    @admin.action(description="Mark selected as read")
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True)
