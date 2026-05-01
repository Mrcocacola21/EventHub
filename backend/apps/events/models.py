from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


def build_unique_slug(instance, value, fallback, max_length):
    base_slug = slugify(value) or fallback
    base_slug = base_slug[:max_length].strip("-") or fallback
    slug = base_slug
    suffix = 1

    queryset = instance.__class__._default_manager.all()
    if instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    while queryset.filter(slug=slug).exists():
        suffix_text = f"-{suffix}"
        prefix_length = max_length - len(suffix_text)
        slug = f"{base_slug[:prefix_length].rstrip('-')}{suffix_text}"
        suffix += 1

    return slug


class EventCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "event category"
        verbose_name_plural = "event categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")

        if not self.slug:
            self.slug = build_unique_slug(
                self,
                self.name,
                fallback="category",
                max_length=self._meta.get_field("slug").max_length,
            )
            if update_fields is not None:
                update_fields = set(update_fields)
                update_fields.add("slug")
                kwargs["update_fields"] = update_fields

        super().save(*args, **kwargs)


class Event(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        PUBLISHED = "PUBLISHED", "Published"
        CANCELED = "CANCELED", "Canceled"
        FINISHED = "FINISHED", "Finished"

    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=280, unique=True, blank=True)
    description = models.TextField()
    category = models.ForeignKey(
        EventCategory,
        on_delete=models.PROTECT,
        related_name="events",
    )
    location = models.CharField(max_length=255)
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    organizer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organized_events",
    )
    max_participants = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    is_published = models.BooleanField(default=False, db_index=True)
    cover_image = models.ImageField(
        upload_to="event_covers/",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["start_datetime"]
        verbose_name = "event"
        verbose_name_plural = "events"

    def __str__(self):
        return self.title

    def clean(self):
        errors = {}

        if (
            self.start_datetime
            and self.end_datetime
            and self.end_datetime <= self.start_datetime
        ):
            errors["end_datetime"] = "End datetime must be after start datetime."

        organizer = getattr(self, "organizer", None)
        if organizer and not (
            organizer.is_superuser
            or organizer.is_organizer
            or organizer.is_admin_role
        ):
            errors["organizer"] = (
                "Only organizer or admin users can organize events."
            )

        if self.max_participants is not None and self.max_participants <= 0:
            errors["max_participants"] = (
                "Max participants must be greater than zero."
            )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            update_fields = set(update_fields)

        if not self.slug:
            self.slug = build_unique_slug(
                self,
                self.title,
                fallback="event",
                max_length=self._meta.get_field("slug").max_length,
            )
            if update_fields is not None:
                update_fields.add("slug")

        self.is_published = self.status == self.Status.PUBLISHED
        if update_fields is not None:
            update_fields.add("is_published")
            kwargs["update_fields"] = update_fields

        super().save(*args, **kwargs)

    def publish(self):
        self.status = self.Status.PUBLISHED
        self.is_published = True
        self.save(update_fields=["status", "is_published", "updated_at"])

    def cancel(self):
        self.status = self.Status.CANCELED
        self.is_published = False
        self.save(update_fields=["status", "is_published", "updated_at"])

    def finish(self):
        self.status = self.Status.FINISHED
        self.is_published = False
        self.save(update_fields=["status", "is_published", "updated_at"])

    @property
    def is_active_for_booking(self):
        return (
            self.status == self.Status.PUBLISHED
            and self.is_published
            and self.start_datetime > timezone.now()
        )
