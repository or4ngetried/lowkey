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


class Follow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following_relations"
    )
    followed = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="follower_relations"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["follower", "followed"], name="unique_user_follow"),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F("followed")),
                name="prevent_self_follow",
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.follower_id == self.followed_id:
            raise ValidationError("You cannot follow your own account.")

    def __str__(self):
        return f"{self.follower} follows {self.followed}"


class PollLike(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="poll_likes"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["poll", "user"], name="unique_user_poll_like")
        ]

    def __str__(self):
        return f"{self.user} likes {self.poll}"


class Comment(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="poll_comments"
    )
    body = models.CharField(max_length=500)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Comment by {self.author} on {self.poll}"


class SocialPost(models.Model):
    """A text-first social post; polls remain a first-class post format."""
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="social_posts"
    )
    body = models.CharField(max_length=1200)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Post by {self.author}: {self.body[:60]}"


class SocialPostLike(models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name="likes")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="social_post_likes"
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["post", "user"], name="unique_social_post_like")
        ]
        ordering = ["-created_at"]


class SocialPostComment(models.Model):
    post = models.ForeignKey(SocialPost, on_delete=models.CASCADE, related_name="comments")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="social_post_comments"
    )
    body = models.CharField(max_length=500)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["created_at"]


class Conversation(models.Model):
    """A one-to-one conversation. Participant IDs are stored in ascending order."""
    participant_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_a"
    )
    participant_b = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="conversations_b"
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["participant_a", "participant_b"], name="unique_direct_conversation"),
            models.CheckConstraint(
                condition=~models.Q(participant_a=models.F("participant_b")),
                name="conversation_distinct_people",
            ),
        ]

    def includes(self, user):
        return user.pk in (self.participant_a_id, self.participant_b_id)

    def other_person(self, user):
        return self.participant_b if self.participant_a_id == user.pk else self.participant_a


class DirectMessage(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_direct_messages"
    )
    body = models.CharField(max_length=2000)
    created_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Message from {self.sender}"
