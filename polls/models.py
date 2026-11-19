import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

CATEGORY_CHOICES = [
    ("everyday", "Everyday"),
    ("music", "Music"),
    ("entertainment", "Entertainment"),
    ("food", "Food"),
    ("gaming", "Gaming"),
    ("sports", "Sports"),
    ("school", "School"),
    ("other", "Other"),
]


class Profile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    bio = models.CharField(max_length=240, blank=True)
    joined_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"@{self.user.username}"


class Poll(models.Model):
    VISIBILITY_CHOICES = [
        ("public", "Public"),
        ("private", "Private · link only"),
    ]

    question = models.CharField(max_length=220)
    description = models.TextField(blank=True)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="polls",
    )
    category = models.CharField(
        max_length=20, choices=CATEGORY_CHOICES, default="everyday"
    )
    visibility = models.CharField(
        max_length=10, choices=VISIBILITY_CHOICES, default="public"
    )
    share_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.question

    @property
    def total_votes(self):
        return self.votes.count()


class Option(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="options")
    text = models.CharField(max_length=180)

    def __str__(self):
        return self.text


class Vote(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="votes")
    option = models.ForeignKey(Option, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="poll_votes",
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["poll", "user"], name="unique_user_poll_vote"
            )
        ]

    def __str__(self):
        return f"{self.user} · {self.option} ({self.poll})"

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.option_id and self.poll_id:
            if self.option.poll_id != self.poll_id:
                raise ValidationError("The selected option must belong to this poll.")
