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


    def test_home_shows_discovery_sections_and_stats(self):
        Vote.objects.create(poll=self.poll, option=self.first, user=self.other_user)
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trending")
        self.assertContains(response, "posts")
        self.assertContains(response, self.poll.question)

    def test_home_category_filter(self):
        self.poll.category = "music"
        self.poll.save(update_fields=["category"])
        response = self.client.get(reverse("home"), {"category": "food"})
        self.assertNotContains(response, self.poll.question)

    def test_home_paginates_public_polls(self):
        for number in range(10):
            poll = Poll.objects.create(
                question=f"Extra question {number}", creator=self.user, visibility="public"
            )
            Option.objects.create(poll=poll, text="Yes")
            Option.objects.create(poll=poll, text="No")
        response = self.client.get(reverse("home"))
        self.assertEqual(response.context["paginator"].per_page, 10)
        self.assertEqual(response.context["page_obj"].number, 1)
        self.assertTrue(response.context["page_obj"].has_next())

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


class SocialFeatureTests(TestCase):
    def setUp(self):
        self.creator = User.objects.create_user(username="creator", password="test-password-123")
        self.member = User.objects.create_user(username="member", password="test-password-123")
        self.poll = Poll.objects.create(question="Best weekend plan?", creator=self.creator)
        self.yes = Option.objects.create(poll=self.poll, text="Outside")
        self.no = Option.objects.create(poll=self.poll, text="At home")

    def test_follow_button_creates_and_toggles_follow(self):
        self.client.login(username="member", password="test-password-123")
        url = reverse("follow_user", args=[self.creator.username])
        self.client.post(url)
        self.assertTrue(self.creator.follower_relations.filter(follower=self.member).exists())
        self.client.post(url)
        self.assertFalse(self.creator.follower_relations.filter(follower=self.member).exists())

    def test_user_cannot_follow_themselves(self):
        self.client.login(username="creator", password="test-password-123")
        self.client.post(reverse("follow_user", args=[self.creator.username]))
        self.assertFalse(self.creator.follower_relations.filter(follower=self.creator).exists())

    def test_following_feed_only_shows_followed_users_posts(self):
        other_poll = Poll.objects.create(question="Another person's question", creator=self.member)
        Option.objects.create(poll=other_poll, text="One")
        Option.objects.create(poll=other_poll, text="Two")
        self.client.login(username="member", password="test-password-123")
        self.client.post(reverse("follow_user", args=[self.creator.username]))
        response = self.client.get(reverse("home"), {"feed": "following"})
        self.assertContains(response, self.poll.question)
        self.assertNotContains(response, other_poll.question)

    def test_like_can_be_added_and_removed(self):
        self.client.login(username="member", password="test-password-123")
        url = reverse("like_poll", args=[self.poll.pk])
        self.client.post(url)
        self.assertEqual(self.poll.likes.count(), 1)
        self.client.post(url)
        self.assertEqual(self.poll.likes.count(), 0)

    def test_comment_is_created_and_shown(self):
        self.client.login(username="member", password="test-password-123")
        response = self.client.post(
            reverse("add_comment", args=[self.poll.pk]),
            {"body": "I like getting outside."},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.poll.comments.count(), 1)
        self.assertContains(self.client.get(reverse("poll_detail", args=[self.poll.pk])), "I like getting outside.")

    def test_comment_author_can_delete_own_comment(self):
        from .models import Comment
        comment = Comment.objects.create(poll=self.poll, author=self.member, body="A thought")
        self.client.login(username="member", password="test-password-123")
        self.client.post(reverse("delete_comment", args=[comment.pk]))
        self.assertFalse(Comment.objects.filter(pk=comment.pk).exists())

    def test_profile_shows_social_counts_and_follow_action(self):
        from .models import Follow
        Follow.objects.create(follower=self.member, followed=self.creator)
        self.client.login(username="member", password="test-password-123")
        response = self.client.get(reverse("profile", args=[self.creator.username]))
        self.assertContains(response, "followers")
        self.assertContains(response, "Following")


class SocialPostAndChatTests(TestCase):
    def setUp(self):
        self.alex = User.objects.create_user(username="alex", password="test-password-123")
        self.sam = User.objects.create_user(username="sam", password="test-password-123")
    def test_user_can_create_text_post(self):
        self.client.login(username="alex", password="test-password-123")
        response = self.client.post(reverse("create_social_post"), {"body": "A test post for the feed."})
        self.assertEqual(response.status_code, 302)
        from .models import SocialPost
        self.assertEqual(SocialPost.objects.get().author, self.alex)
    def test_text_posts_appear_in_feed(self):
        from .models import SocialPost
        SocialPost.objects.create(author=self.alex, body="Hello social feed")
        self.assertContains(self.client.get(reverse("home")), "Hello social feed")
    def test_start_chat_requires_existing_follow_connection(self):
        self.client.login(username="alex", password="test-password-123")
        self.client.post(reverse("start_conversation", args=["sam"]))
        from .models import Conversation
        self.assertEqual(Conversation.objects.count(), 0)
    def test_one_way_follow_is_not_enough_to_start_chat(self):
        from .models import Conversation, Follow
        Follow.objects.create(follower=self.alex, followed=self.sam)
        self.client.login(username="alex", password="test-password-123")
        self.client.post(reverse("start_conversation", args=["sam"]))
        self.assertEqual(Conversation.objects.count(), 0)

    def test_chat_participants_can_exchange_messages(self):
        from .models import Conversation, DirectMessage, Follow
        Follow.objects.create(follower=self.alex, followed=self.sam)
        Follow.objects.create(follower=self.sam, followed=self.alex)
        self.client.login(username="alex", password="test-password-123")
        response = self.client.post(reverse("start_conversation", args=["sam"]))
        conversation = Conversation.objects.get()
        self.assertEqual(response.url, reverse("conversation_detail", args=[conversation.pk]))
        self.client.post(reverse("conversation_detail", args=[conversation.pk]), {"body": "Hi Sam"})
        self.assertEqual(DirectMessage.objects.get().body, "Hi Sam")
    def test_non_participant_cannot_read_conversation(self):
        from .models import Conversation
        third = User.objects.create_user(username="third", password="test-password-123")
        conversation = Conversation.objects.create(participant_a=self.alex, participant_b=self.sam)
        self.client.login(username="third", password="test-password-123")
        self.assertEqual(self.client.get(reverse("conversation_detail", args=[conversation.pk])).status_code, 403)
