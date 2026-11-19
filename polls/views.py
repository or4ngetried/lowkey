from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import IntegrityError, transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.core.paginator import Paginator
from django.utils import timezone
from datetime import timedelta

from .forms import ProfileForm, PollForm, SignUpForm, VoteForm
from .models import CATEGORY_CHOICES, Option, Poll, Profile, Vote


def ensure_profile(user):
    Profile.objects.get_or_create(user=user)


def home(request):
    polls = (
        Poll.objects.filter(is_active=True, visibility="public")
        .select_related("creator")
        .prefetch_related("options")
        .annotate(
            vote_count=Count("votes", distinct=True),
            option_count=Count("options", distinct=True),
        )
    )
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "")
    sort = request.GET.get("sort", "newest")

    if query:
        polls = polls.filter(
            Q(question__icontains=query)
            | Q(description__icontains=query)
            | Q(creator__username__icontains=query)
        )
    if category in dict(CATEGORY_CHOICES):
        polls = polls.filter(category=category)
    else:
        category = ""

    if sort == "popular":
        polls = polls.order_by("-vote_count", "-created_at")
    elif sort == "oldest":
        polls = polls.order_by("created_at")
    else:
        sort = "newest"
        polls = polls.order_by("-created_at")

    paginator = Paginator(polls, 9)
    page_obj = paginator.get_page(request.GET.get("page"))
    trending = (
        Poll.objects.filter(is_active=True, visibility="public", votes__isnull=False)
        .select_related("creator")
        .annotate(vote_count=Count("votes", distinct=True))
        .order_by("-vote_count", "-created_at")[:3]
    )
    community_stats = {
        "polls": Poll.objects.filter(is_active=True, visibility="public").count(),
        "members": User.objects.count(),
        "votes": Vote.objects.filter(poll__visibility="public", poll__is_active=True).count(),
    }

    return render(
        request,
        "polls/home.html",
        {
            "polls": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "query": query,
            "selected_category": category,
            "selected_sort": sort,
            "categories": CATEGORY_CHOICES,
            "trending": trending,
            "community_stats": community_stats,
        },
    )


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
    return render(request, "polls/my_polls.html", {"polls": polls})


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
        },
    )
