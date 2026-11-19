from django.db import migrations, models
import django.db.models.deletion


def link_votes_to_polls(apps, schema_editor):
    Vote = apps.get_model("polls", "Vote")
    alias = schema_editor.connection.alias

    # Older versions only constrained (option, user), so a user may have
    # multiple votes on different options in one poll. Keep the earliest.
    seen = set()
    votes = (
        Vote.objects.using(alias)
        .select_related("option")
        .order_by("created_at", "pk")
    )
    for vote in votes.iterator():
        poll_id = vote.option.poll_id
        key = (poll_id, vote.user_id)
        if key in seen:
            vote.delete(using=alias)
            continue
        seen.add(key)
        Vote.objects.using(alias).filter(pk=vote.pk).update(poll_id=poll_id)


class Migration(migrations.Migration):
    dependencies = [
        ("polls", "0002_poll_category_poll_share_token_poll_visibility_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="vote",
            name="poll",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="votes",
                to="polls.poll",
            ),
        ),
        migrations.RunPython(link_votes_to_polls, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="vote",
            name="poll",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="votes",
                to="polls.poll",
            ),
        ),
        migrations.RemoveConstraint(
            model_name="vote",
            name="unique_user_option",
        ),
        migrations.AddConstraint(
            model_name="vote",
            constraint=models.UniqueConstraint(
                fields=("poll", "user"), name="unique_user_poll_vote"
            ),
        ),
    ]
