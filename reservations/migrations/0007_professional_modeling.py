import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
from django.utils.text import slugify


def populate_event_slugs(apps, schema_editor):
    Event = apps.get_model("reservations", "Event")
    for event in Event.objects.order_by("pk").all():
        if not event.slug:
            base = slugify(event.title) or "event"
            slug = base
            n = 1
            while Event.objects.filter(slug=slug).exclude(pk=event.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            event.slug = slug
            event.save(update_fields=["slug"])


def populate_category_slugs(apps, schema_editor):
    Category = apps.get_model("reservations", "Category")
    for category in Category.objects.all():
        if not category.slug:
            base = slugify(category.name) or "category"
            slug = base
            n = 1
            while Category.objects.filter(slug=slug).exclude(pk=category.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            category.slug = slug
            category.save(update_fields=["slug"])


class Migration(migrations.Migration):

    dependencies = [
        ("reservations", "0006_category_deleted_at"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        # ===== Event: rename fields =====
        migrations.RenameField(model_name="event", old_name="date", new_name="start_date"),
        migrations.RenameField(model_name="event", old_name="time", new_name="start_time"),
        migrations.RenameField(model_name="event", old_name="location", new_name="venue"),
        # ===== Event: add slug (two-step for uniqueness) =====
        migrations.AddField(
            model_name="event",
            name="slug",
            field=models.SlugField(blank=True, default="", max_length=220),
            preserve_default=False,
        ),
        migrations.RunPython(populate_event_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="event",
            name="slug",
            field=models.SlugField(blank=True, max_length=220, unique=True),
        ),
        # ===== Event: new fields =====
        migrations.AddField(
            model_name="event",
            name="address",
            field=models.CharField(blank=True, default="", max_length=500),
        ),
        migrations.AddField(
            model_name="event",
            name="end_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="end_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="event",
            name="price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="event",
            name="status",
            field=models.CharField(
                choices=[
                    ("draft", "Draft"),
                    ("published", "Published"),
                    ("cancelled", "Cancelled"),
                    ("completed", "Completed"),
                ],
                db_index=True,
                default="published",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="published_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.RemoveField(model_name="event", name="is_active"),
        migrations.AlterModelOptions(
            name="event",
            options={"ordering": ["start_date", "start_time"]},
        ),
        # ===== Event: audit fields =====
        migrations.AddField(
            model_name="event",
            name="created_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="event_created", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="updated_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="event_updated", to=settings.AUTH_USER_MODEL,
            ),
        ),
        # ===== Category: slug (two-step) =====
        migrations.AddField(
            model_name="category",
            name="slug",
            field=models.SlugField(blank=True, default="", max_length=80),
            preserve_default=False,
        ),
        migrations.RunPython(populate_category_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="category",
            name="slug",
            field=models.SlugField(blank=True, max_length=80, unique=True),
        ),
        # ===== Category: new fields =====
        migrations.AddField(
            model_name="category",
            name="description",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="category",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="category",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="category",
            name="created_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="category_created", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="category",
            name="updated_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="category_updated", to=settings.AUTH_USER_MODEL,
            ),
        ),
        # ===== Notification: replace is_read with read_at =====
        migrations.RemoveField(model_name="notification", name="is_read"),
        migrations.AddField(
            model_name="notification",
            name="read_at",
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AlterField(
            model_name="notification",
            name="link",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="notification",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="notification",
            name="created_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="notification_created", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="notification",
            name="updated_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="notification_updated", to=settings.AUTH_USER_MODEL,
            ),
        ),
        # ===== Reservation: add db_index + audit =====
        migrations.AlterField(
            model_name="reservation",
            name="status",
            field=models.CharField(
                choices=[("confirmed", "Confirmed"), ("cancelled", "Cancelled")],
                db_index=True, default="confirmed", max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="reservation",
            name="created_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="reservation_created", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="reservation",
            name="updated_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="reservation_updated", to=settings.AUTH_USER_MODEL,
            ),
        ),
        # ===== Review: audit =====
        migrations.AddField(
            model_name="review",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="review",
            name="created_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="review_created", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="review",
            name="updated_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="review_updated", to=settings.AUTH_USER_MODEL,
            ),
        ),
        # ===== Favorite: audit =====
        migrations.AddField(
            model_name="favorite",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="favorite",
            name="created_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="favorite_created", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="favorite",
            name="updated_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="favorite_updated", to=settings.AUTH_USER_MODEL,
            ),
        ),
        # ===== UserProfile: new fields =====
        migrations.AddField(
            model_name="userprofile",
            name="gender",
            field=models.CharField(
                blank=True,
                choices=[("M", "Male"), ("F", "Female"), ("O", "Other"), ("N", "Prefer not to say")],
                default="", max_length=1,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="phone",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="location",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="website",
            field=models.URLField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="created_at",
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="userprofile",
            name="updated_at",
            field=models.DateTimeField(auto_now=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="userprofile",
            name="created_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="userprofile_created", to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="updated_by",
            field=models.ForeignKey(
                blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                related_name="userprofile_updated", to=settings.AUTH_USER_MODEL,
            ),
        ),
    ]
