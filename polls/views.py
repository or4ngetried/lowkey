from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta
import os

from .forms import CommentForm, ProfileForm, PollForm, SignUpForm, VoteForm, SocialPostForm, DirectMessageForm
from .models import (CATEGORY_CHOICES, Comment, Follow, Option, Poll, PollLike, Profile, Vote, SocialPost, SocialPostLike, SocialPostComment, Conversation, DirectMessage)


def ensure_profile(user):
    Profile.objects.get_or_create(user=user)


def home(request):
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "newest")
    feed = request.GET.get("feed", "for-you")
    followed_ids = []
    if feed == "following" and request.user.is_authenticated:
        followed_ids = list(Follow.objects.filter(follower=request.user).values_list("followed_id", flat=True))
    else:
        feed = "for-you"

    poll_qs = (Poll.objects.filter(is_active=True, visibility="public")
        .select_related("creator").prefetch_related("options")
        .annotate(vote_count=Count("votes", distinct=True), option_count=Count("options", distinct=True), like_count=Count("likes", distinct=True)))
    post_qs = SocialPost.objects.select_related("author").annotate(like_count=Count("likes", distinct=True), comment_count=Count("comments", distinct=True))
    if feed == "following":
        poll_qs = poll_qs.filter(creator_id__in=followed_ids)
        post_qs = post_qs.filter(author_id__in=followed_ids)
    if query:
        poll_qs = poll_qs.filter(Q(question__icontains=query) | Q(description__icontains=query) | Q(creator__username__icontains=query))
        post_qs = post_qs.filter(Q(body__icontains=query) | Q(author__username__icontains=query))
    if category in dict(CATEGORY_CHOICES):
        poll_qs = poll_qs.filter(category=category)
        post_qs = post_qs.none() if category else post_qs
    else:
        category = ""
    polls = list(poll_qs)
    posts = list(post_qs)
    items = [{"kind": "poll", "item": obj, "created_at": obj.created_at, "likes": obj.like_count, "votes": obj.vote_count} for obj in polls]
    items += [{"kind": "post", "item": obj, "created_at": obj.created_at, "likes": obj.like_count, "votes": 0} for obj in posts]
    if sort == "popular":
        items.sort(key=lambda x: (x["likes"], x["votes"], x["created_at"]), reverse=True)
    elif sort == "oldest":
        items.sort(key=lambda x: x["created_at"])
    else:
        sort = "newest"
        items.sort(key=lambda x: x["created_at"], reverse=True)

    paginator = Paginator(items, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    liked_poll_ids, liked_post_ids = set(), set()
    if request.user.is_authenticated:
        page_poll_ids = [x["item"].pk for x in page_obj.object_list if x["kind"] == "poll"]
        page_post_ids = [x["item"].pk for x in page_obj.object_list if x["kind"] == "post"]
        liked_poll_ids = set(PollLike.objects.filter(user=request.user, poll_id__in=page_poll_ids).values_list("poll_id", flat=True))
        liked_post_ids = set(SocialPostLike.objects.filter(user=request.user, post_id__in=page_post_ids).values_list("post_id", flat=True))
    trending = (Poll.objects.filter(is_active=True, visibility="public", votes__isnull=False)
        .select_related("creator").annotate(vote_count=Count("votes", distinct=True)).order_by("-vote_count", "-created_at")[:3])
    community_stats = {
        "polls": Poll.objects.filter(is_active=True, visibility="public").count() + SocialPost.objects.count(),
        "members": User.objects.count(),
        "votes": Vote.objects.filter(poll__visibility="public", poll__is_active=True).count(),
    }
    return render(request, "polls/home.html", {
        "feed_items": page_obj.object_list, "page_obj": page_obj, "paginator": paginator,
        "query": query, "selected_category": category, "selected_sort": sort,
        "categories": CATEGORY_CHOICES, "trending": trending, "community_stats": community_stats,
        "feed": feed, "following_count": Follow.objects.filter(follower=request.user).count() if request.user.is_authenticated else 0,
        "liked_poll_ids": liked_poll_ids, "liked_post_ids": liked_post_ids,
        "post_form": SocialPostForm(),
    })


def signup(request):
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            ensure_profile(user)
            login(request, user)
            messages.success(request, "Your account is ready. Welcome to lowkey.")
            return redirect("home")
    else:
        form = SignUpForm()
    return render(request, "registration/signup.html", {"form": form})


@login_required
def create_poll(request):
    if request.method == "POST":
        form = PollForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                poll = Poll.objects.create(
                    question=form.cleaned_data["question"],
                    description=form.cleaned_data["description"],
                    category=form.cleaned_data["category"],
                    visibility=form.cleaned_data["visibility"],
                    creator=request.user,
                )
                Option.objects.bulk_create(
                    [Option(poll=poll, text=text) for text in form.cleaned_data["options"]]
                )
            messages.success(request, "Your poll has been created.")
            if poll.visibility == "private":
                return redirect("shared_poll", token=poll.share_token)
            return redirect("poll_detail", poll_id=poll.pk)
    else:
        form = PollForm()
    return render(request, "polls/create.html", {"form": form})


def poll_detail(request, poll_id):
    poll = get_object_or_404(
        Poll.objects.select_related("creator"),
        pk=poll_id,
        is_active=True,
        visibility="public",
    )
    return render_poll(request, poll, False)


def shared_poll(request, token):
    poll = get_object_or_404(
        Poll.objects.select_related("creator"),
        share_token=token,
        is_active=True,
        visibility="private",
    )
    return render_poll(request, poll, True)


def render_poll(request, poll, shared):
    voted = (
        request.user.is_authenticated
        and Vote.objects.filter(poll=poll, user=request.user).exists()
    )
    return render(
        request,
        "polls/detail.html",
        {
            "poll": poll,
            "form": VoteForm(poll=poll),
            "already_voted": voted,
            "is_shared": shared,
            "comments": poll.comments.select_related("author").all()[:40],
            "comment_form": CommentForm(),
            "like_count": poll.likes.count(),
            "liked": request.user.is_authenticated and poll.likes.filter(user=request.user).exists(),
        },
    )


@login_required
def vote(request, poll_id=None, token=None):
    if token:
        poll = get_object_or_404(
            Poll, share_token=token, visibility="private", is_active=True
        )
    else:
        poll = get_object_or_404(
            Poll, pk=poll_id, visibility="public", is_active=True
        )

    destination = (
        redirect("shared_poll", token=poll.share_token)
        if token
        else redirect("poll_detail", poll_id=poll.pk)
    )
    if request.method != "POST":
        return destination

    form = VoteForm(request.POST, poll=poll)
    if not form.is_valid():
        messages.error(request, "Choose one of the available answer options.")
        return destination

    if Vote.objects.filter(poll=poll, user=request.user).exists():
        messages.info(request, "You've already voted in this poll.")
    else:
        try:
            with transaction.atomic():
                Vote.objects.create(
                    poll=poll,
                    option=form.cleaned_data["option"],
                    user=request.user,
                )
            messages.success(request, "Vote counted. Thanks for taking part.")
        except IntegrityError:
            # The database constraint also protects against two requests arriving
            # at almost exactly the same time.
            messages.info(request, "Your vote was already counted.")

    if token:
        return redirect("shared_results", token=poll.share_token)
    return redirect("results", poll_id=poll.pk)


def results(request, poll_id):
    poll = get_object_or_404(Poll, pk=poll_id, visibility="public")
    return show_results(request, poll)


def shared_results(request, token):
    poll = get_object_or_404(Poll, share_token=token, visibility="private")
    return show_results(request, poll)


def show_results(request, poll):
    total = poll.total_votes
    rows = []
    for option in poll.options.all():
        count = option.votes.count()
        rows.append(
            {
                "option": option,
                "votes": count,
                "percent": round(count * 100 / total) if total else 0,
            }
        )
    return render(
        request,
        "polls/results.html",
        {"poll": poll, "results": rows, "total": total},
    )


@login_required
def my_polls(request):
    polls = (
        Poll.objects.filter(creator=request.user)
        .prefetch_related("options")
        .annotate(vote_count=Count("votes", distinct=True))
    )
    social_posts = SocialPost.objects.filter(author=request.user).order_by("-created_at")
    return render(request, "polls/my_polls.html", {"polls": polls, "social_posts": social_posts})


def profile(request, username):
    person = get_object_or_404(User, username=username)
    ensure_profile(person)
    profile_obj = person.profile
    form = None

    if request.user == person:
        if request.method == "POST":
            form = ProfileForm(request.POST)
            if form.is_valid():
                profile_obj.bio = form.cleaned_data["bio"]
                profile_obj.save(update_fields=["bio"])
                messages.success(request, "Profile updated.")
                return redirect("profile", username=username)
        else:
            form = ProfileForm(initial={"bio": profile_obj.bio})

    created = Poll.objects.filter(
        creator=person, visibility="public", is_active=True
    ).order_by("-created_at")
    votes = (
        Vote.objects.filter(user=person, poll__visibility="public", poll__is_active=True)
        .select_related("option", "poll")
        .order_by("-created_at")[:20]
    )
    return render(
        request,
        "polls/profile.html",
        {
            "viewed_user": person,
            "profile_obj": profile_obj,
            "created": created,
            "votes": votes,
            "form": form,
            "follower_count": Follow.objects.filter(followed=person).count(),
            "following_count": Follow.objects.filter(follower=person).count(),
            "is_following": request.user.is_authenticated and request.user != person and Follow.objects.filter(follower=request.user, followed=person).exists(),
            "followers": User.objects.filter(follower_relations__followed=person).distinct()[:8],
            "social_posts": SocialPost.objects.filter(author=person).order_by("-created_at")[:20],
            "profile_post_count": created.count() + SocialPost.objects.filter(author=person).count(),
            "can_message": request.user.is_authenticated and request.user != person and Follow.objects.filter(follower=request.user, followed=person).exists() and Follow.objects.filter(follower=person, followed=request.user).exists(),
        },
    )


@login_required
def follow_user(request, username):
    if request.method != "POST":
        return redirect("profile", username=username)
    person = get_object_or_404(User, username=username)
    if person == request.user:
        messages.info(request, "You cannot follow your own account.")
        return redirect("profile", username=username)
    relation, created = Follow.objects.get_or_create(follower=request.user, followed=person)
    if created:
        messages.success(request, f"You're now following @{person.username}.")
    else:
        relation.delete()
        messages.info(request, f"You unfollowed @{person.username}.")
    return redirect("profile", username=username)


@login_required
def like_poll(request, poll_id=None, token=None):
    if token:
        poll = get_object_or_404(Poll, share_token=token, visibility="private", is_active=True)
        destination = redirect("shared_poll", token=poll.share_token)
    else:
        poll = get_object_or_404(Poll, pk=poll_id, visibility="public", is_active=True)
        destination = redirect("poll_detail", poll_id=poll.pk)
    if request.method == "POST":
        like, created = PollLike.objects.get_or_create(poll=poll, user=request.user)
        if not created:
            like.delete()
    return destination


@login_required
def add_comment(request, poll_id=None, token=None):
    if token:
        poll = get_object_or_404(Poll, share_token=token, visibility="private", is_active=True)
        destination = redirect("shared_poll", token=poll.share_token)
    else:
        poll = get_object_or_404(Poll, pk=poll_id, visibility="public", is_active=True)
        destination = redirect("poll_detail", poll_id=poll.pk)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            Comment.objects.create(poll=poll, author=request.user, body=form.cleaned_data["body"].strip())
            messages.success(request, "Your comment was posted.")
        else:
            messages.error(request, "Write a comment of 1–500 characters.")
    return destination


@login_required
def delete_comment(request, comment_id):
    comment = get_object_or_404(Comment.objects.select_related("poll"), pk=comment_id)
    poll = comment.poll
    if request.method == "POST" and comment.author_id == request.user.id:
        comment.delete()
        messages.success(request, "Comment deleted.")
    elif comment.author_id != request.user.id:
        messages.error(request, "You can only delete your own comments.")
    if poll.visibility == "private":
        return redirect("shared_poll", token=poll.share_token)
    return redirect("poll_detail", poll_id=poll.pk)


@login_required
def create_social_post(request):
    if request.method == "POST":
        form = SocialPostForm(request.POST)
        if form.is_valid():
            SocialPost.objects.create(author=request.user, body=form.cleaned_data["body"].strip())
            messages.success(request, "Your post is live.")
        else:
            messages.error(request, "Your post must be between 1 and 1,200 characters.")
    return redirect("home")


def social_post_detail(request, post_id):
    post = get_object_or_404(SocialPost.objects.select_related("author"), pk=post_id)
    comments = post.comments.select_related("author").all()
    liked = request.user.is_authenticated and post.likes.filter(user=request.user).exists()
    return render(request, "polls/post_detail.html", {"post": post, "comments": comments, "liked": liked, "comment_form": CommentForm()})


@login_required
def like_social_post(request, post_id):
    post = get_object_or_404(SocialPost, pk=post_id)
    if request.method == "POST":
        like, created = SocialPostLike.objects.get_or_create(post=post, user=request.user)
        if not created:
            like.delete()
    return redirect("social_post_detail", post_id=post.pk)


@login_required
def comment_social_post(request, post_id):
    post = get_object_or_404(SocialPost, pk=post_id)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            SocialPostComment.objects.create(post=post, author=request.user, body=form.cleaned_data["body"].strip())
    return redirect("social_post_detail", post_id=post.pk)


def _get_or_create_conversation(user1, user2):
    if user1.pk == user2.pk:
        return None
    first, second = sorted([user1, user2], key=lambda u: u.pk)
    conversation, _ = Conversation.objects.get_or_create(participant_a=first, participant_b=second)
    return conversation


@login_required
def start_conversation(request, username):
    if request.method != "POST":
        return redirect("profile", username=username)
    person = get_object_or_404(User, username=username)
    if person == request.user:
        return redirect("profile", username=username)
    # Restrict new chats to people with an existing follow connection in either direction.
    connected = Follow.objects.filter(follower=request.user, followed=person).exists() and Follow.objects.filter(follower=person, followed=request.user).exists()
    if not connected:
        messages.info(request, "You both need to follow each other before starting a private chat.")
        return redirect("profile", username=username)
    conversation = _get_or_create_conversation(request.user, person)
    return redirect("conversation_detail", conversation_id=conversation.pk)


@login_required
def message_inbox(request):
    conversations = Conversation.objects.filter(Q(participant_a=request.user) | Q(participant_b=request.user)).select_related("participant_a", "participant_b").prefetch_related("messages")
    entries = []
    for conversation in conversations:
        other = conversation.other_person(request.user)
        last_message = conversation.messages.order_by("-created_at").first()
        unread = conversation.messages.filter(read_at__isnull=True).exclude(sender=request.user).count()
        entries.append({"conversation": conversation, "other": other, "last_message": last_message, "unread": unread})
    return render(request, "polls/inbox.html", {"entries": entries})


@login_required
def conversation_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation.objects.select_related("participant_a", "participant_b"), pk=conversation_id)
    if not conversation.includes(request.user):
        return HttpResponseForbidden("This conversation is private.")
    other = conversation.other_person(request.user)
    if request.method == "POST":
        form = DirectMessageForm(request.POST)
        if form.is_valid():
            DirectMessage.objects.create(conversation=conversation, sender=request.user, body=form.cleaned_data["body"].strip())
            conversation.updated_at = timezone.now()
            conversation.save(update_fields=["updated_at"])
            return redirect("conversation_detail", conversation_id=conversation.pk)
    else:
        form = DirectMessageForm()
    conversation.messages.filter(read_at__isnull=True).exclude(sender=request.user).update(read_at=timezone.now())
    messages_list = list(conversation.messages.select_related("sender").order_by("created_at"))[-200:]
    return render(request, "polls/conversation.html", {"conversation": conversation, "other": other, "chat_messages": messages_list, "form": form})


@login_required
def message_updates(request, conversation_id):
    conversation = get_object_or_404(Conversation, pk=conversation_id)
    if not conversation.includes(request.user):
        return HttpResponseForbidden("This conversation is private.")
    conversation.messages.filter(read_at__isnull=True).exclude(sender=request.user).update(read_at=timezone.now())
    data = [{"id": m.pk, "sender": m.sender.username, "mine": m.sender_id == request.user.pk, "body": m.body, "created": timezone.localtime(m.created_at).strftime("%b %-d, %I:%M %p") if os.name != "nt" else timezone.localtime(m.created_at).strftime("%b %#d, %I:%M %p")} for m in list(conversation.messages.select_related("sender").order_by("created_at"))[-100:]]
    return JsonResponse({"messages": data})
