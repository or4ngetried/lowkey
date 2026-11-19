from django.contrib.auth import get_user_model
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.urls import reverse

from .models import Option, Poll, Vote

User = get_user_model()


class PollFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pollmaker", password="test-password-123"
        )
        self.other_user = User.objects.create_user(
            username="voter", password="test-password-123"
        )
        self.poll = Poll.objects.create(
            question="Which season is best?",
            creator=self.user,
            visibility="public",
        )
        self.first = Option.objects.create(poll=self.poll, text="Summer")
        self.second = Option.objects.create(poll=self.poll, text="Autumn")

    def test_home_only_lists_public_polls(self):
        private = Poll.objects.create(
            question="Private question", creator=self.user, visibility="private"
        )
        Option.objects.create(poll=private, text="A")
        Option.objects.create(poll=private, text="B")

        response = self.client.get(reverse("home"))

        self.assertContains(response, self.poll.question)
        self.assertNotContains(response, private.question)

    def test_private_poll_requires_share_token(self):
        private = Poll.objects.create(
            question="Only by link", creator=self.user, visibility="private"
        )
        Option.objects.create(poll=private, text="Yes")
        Option.objects.create(poll=private, text="No")

        self.assertEqual(self.client.get(reverse("poll_detail", args=[private.pk])).status_code, 404)
        self.assertEqual(
            self.client.get(reverse("shared_poll", args=[private.share_token])).status_code,
            200,
        )

    def test_vote_requires_login(self):
        response = self.client.post(
            reverse("vote", args=[self.poll.pk]), {"option": self.first.pk}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vote.objects.count(), 0)

    def test_user_can_vote_once_per_poll(self):
        self.client.login(username="voter", password="test-password-123")
        response = self.client.post(
            reverse("vote", args=[self.poll.pk]), {"option": self.first.pk}
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Vote.objects.filter(poll=self.poll, user=self.other_user).count(), 1)

        self.client.post(
            reverse("vote", args=[self.poll.pk]), {"option": self.second.pk}
        )
        self.assertEqual(Vote.objects.filter(poll=self.poll, user=self.other_user).count(), 1)
        self.assertEqual(Vote.objects.get(poll=self.poll, user=self.other_user).option, self.first)

    def test_database_rejects_second_vote_for_same_poll(self):
        Vote.objects.create(poll=self.poll, option=self.first, user=self.other_user)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Vote.objects.create(
                    poll=self.poll, option=self.second, user=self.other_user
                )

    def test_invalid_option_from_another_poll_is_rejected(self):
        other_poll = Poll.objects.create(
            question="Other poll", creator=self.user, visibility="public"
        )
        foreign_option = Option.objects.create(poll=other_poll, text="Not here")
        self.client.login(username="voter", password="test-password-123")

        self.client.post(
            reverse("vote", args=[self.poll.pk]), {"option": foreign_option.pk}
        )

        self.assertFalse(Vote.objects.filter(poll=self.poll, user=self.other_user).exists())
