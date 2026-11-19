from django.contrib import admin

from .models import Option, Poll, Profile, Vote


class OptionInline(admin.TabularInline):
    model = Option
    extra = 0


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    list_display = ("question", "creator", "category", "visibility", "created_at", "is_active")
    list_filter = ("category", "visibility", "is_active")
    search_fields = ("question", "creator__username")
    inlines = [OptionInline]


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("poll", "option", "user", "created_at")
    list_filter = ("created_at",)
    search_fields = ("poll__question", "user__username", "option__text")


admin.site.register(Profile)
